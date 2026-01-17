"""
Executor Engine - The Main OODA Loop

Ties all modules together using the OODA Loop (Observe-Orient-Decide-Act).
This is the main runtime engine for executing AOL workflows.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Set

from paws.core.models import AOLWorkflow, AOLStep
from paws.core.registry import Registry
from paws.aol_parser import load_aol_file, validate_dependencies, extract_variable_references
from paws.state_manager import (
    EventLog, initialize_state, append_event, 
    get_last_successful_step, get_loop_counter
)
from paws.mcp_client import (
    ExecutionResult, load_extension_instance, send_payload, discover_tools
)
from paws.security import verify_entitlements, extract_paths_from_inputs
from paws.validator import validate_step, trigger_feedback_loop


class ExecutorEngine:
    """
    The main execution engine for AOL workflows.
    
    Implements the OODA Loop:
    - Observe: Check current state from event log
    - Orient: Determine next pending step
    - Decide: Verify entitlements
    - Act: Execute tool and validate
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the executor engine.
        
        Args:
            log_dir: Directory for event logs. Defaults to ./.paws_logs/
        """
        self.registry = Registry()
        self.log_dir = Path(log_dir) if log_dir else Path("./.paws_logs")
        self.context: Dict[str, Dict[str, Any]] = {}  # step_id -> outputs
        self.loop_counters: Dict[str, int] = {}  # loop_id -> counter
        self.event_log: Optional[EventLog] = None
        self.workflow: Optional[AOLWorkflow] = None
        
    def run_workflow(self, aol_file: str, resume: bool = False) -> bool:
        """
        Execute an AOL workflow file.
        
        Args:
            aol_file: Path to the .aol file
            resume: If True, attempt to resume from last successful step
            
        Returns:
            True if workflow completed successfully
        """
        # Step 1: Load and validate AOL file
        print(f"Loading workflow from {aol_file}...")
        try:
            self.workflow = load_aol_file(aol_file)
        except Exception as e:
            print(f"Failed to load AOL file: {e}")
            return False
        
        # Validate dependencies
        is_valid, errors = validate_dependencies(self.workflow, self.registry)
        if not is_valid:
            print("Validation errors:")
            for err in errors:
                print(f"  - {err}")
            return False
        
        print(f"Provider: {self.workflow.provider.name}")
        print(f"User Prompt: {self.workflow.user_inputs.prompt}")
        
        # Step 2: Initialize state (event log)
        log_path = self.log_dir / f"{Path(aol_file).stem}.json"
        
        if resume and log_path.exists():
            print(f"Resuming from event log: {log_path}")
            self.event_log = EventLog.load(log_path)
        else:
            self.event_log = initialize_state(
                self.workflow.user_inputs.model_dump(), 
                str(log_path)
            )
        
        # Store user_inputs and provider in context for variable interpolation
        self.context["user_inputs"] = self.workflow.user_inputs.model_dump()
        self.context["provider"] = self.workflow.provider.model_dump()
        
        # Step 3: Determine starting point
        last_success = get_last_successful_step(self.event_log) if resume else None
        start_index = 0
        if last_success:
            for idx, step in enumerate(self.workflow.steps):
                if step.id == last_success:
                    start_index = idx + 1
                    print(f"Resuming after step '{last_success}'")
                    break
        
        print("Starting execution loop...")
        
        # Step 4: Execute steps in order (with control flow)
        step_index = start_index
        steps = self.workflow.steps
        step_id_to_index = {step.id: idx for idx, step in enumerate(steps)}
        
        while step_index < len(steps):
            step = steps[step_index]
            
            # Handle loop_begin
            if step.loop_begin:
                step_index = self._handle_loop_begin(step, step_index)
                continue
            
            # Handle loop_end
            if step.loop_end:
                step_index = self._handle_loop_end(step, step_index, step_id_to_index)
                continue
            
            # Handle switch (routing step)
            if step.switch:
                step_index = self._handle_switch(step, step_index, step_id_to_index)
                continue
            
            # Execute regular step
            success = self._execute_step(step)
            if not success:
                # Check on_failure strategy
                if not self._handle_failure(step):
                    append_event(self.event_log, "WORKFLOW_ABORTED", step.id, 
                                {"reason": "Step failed with abort strategy"})
                    return False
            
            step_index += 1
        
        append_event(self.event_log, "WORKFLOW_COMPLETE")
        print("\nWorkflow completed successfully!")
        return True
    
    def _execute_step(self, step: AOLStep) -> bool:
        """
        Execute a single step with the OODA loop pattern.
        
        Returns:
            True if step executed successfully
        """
        print(f"\n--- Executing Step ID: {step.id} ---")
        if step.description:
            print(f"Description: {step.description}")
        
        # Check condition
        if step.condition:
            condition_result = self._evaluate_condition(step.condition.if_)
            if not condition_result:
                print(f"Condition '{step.condition.if_}' is false, skipping step")
                append_event(self.event_log, "STEP_SKIPPED", step.id, 
                            {"reason": "Condition false"})
                self.context[step.id] = {"skipped": True}
                return True
        
        append_event(self.event_log, "STEP_START", step.id)
        
        # Decide: Verify entitlements
        if step.extension:
            paths = extract_paths_from_inputs(step.inputs)
            for path in paths:
                allowed, reason = verify_entitlements(
                    self.workflow.provider.entitlements,
                    step.extension,
                    step.tool or "default",
                    path
                )
                if not allowed:
                    print(f"Security: Access denied - {reason}")
                    append_event(self.event_log, "STEP_FAILURE", step.id,
                                {"error": f"Entitlement check failed: {reason}"})
                    return False
        
        # Act: Execute the tool
        if not step.extension:
            print(f"Warning: Step '{step.id}' has no extension defined")
            return True
        
        ext_def = self.registry.get_extension(step.extension)
        if not ext_def:
            print(f"Error: Extension '{step.extension}' not found")
            append_event(self.event_log, "STEP_FAILURE", step.id,
                        {"error": f"Extension not found: {step.extension}"})
            return False
        
        try:
            extension_instance = load_extension_instance(ext_def)
            
            # Interpolate variables in inputs
            interpolated_inputs = self._interpolate_dict(step.inputs)
            
            tool_name = step.tool or "execute_command"  # Default for Bash
            print(f"Calling {step.extension}.{tool_name} with: {interpolated_inputs}")
            
            result = send_payload(extension_instance, tool_name, interpolated_inputs)
            
            # Store result in context
            self.context[step.id] = result.to_context()
            
            # Validate step output
            is_valid, validation_errors = validate_step(result, step.outputs, step.id)
            
            if result.is_error or not is_valid:
                print(f"Step failed: {result.stderr or validation_errors}")
                append_event(self.event_log, "STEP_FAILURE", step.id, {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "validation_errors": validation_errors
                })
                return False
            
            print(f"Output: {result.stdout[:200]}..." if len(result.stdout) > 200 else f"Output: {result.stdout}")
            append_event(self.event_log, "STEP_SUCCESS", step.id, {
                "stdout": result.stdout,
                "exit_code": result.exit_code
            })
            return True
            
        except Exception as e:
            print(f"Execution error: {e}")
            import traceback
            traceback.print_exc()
            append_event(self.event_log, "STEP_FAILURE", step.id, {"error": str(e)})
            return False
    
    def _handle_loop_begin(self, step: AOLStep, current_index: int) -> int:
        """Handle loop_begin marker - increment counter and check max_iterations."""
        loop_id = step.id
        
        # Increment counter (starts at 0, incremented BEFORE body)
        if loop_id not in self.loop_counters:
            self.loop_counters[loop_id] = 0
        self.loop_counters[loop_id] += 1
        counter = self.loop_counters[loop_id]
        
        # Store counter in context for variable interpolation
        self.context[loop_id] = {"counter": str(counter)}
        
        print(f"\n=== Loop '{loop_id}' iteration {counter} ===")
        append_event(self.event_log, "LOOP_ITERATION", loop_id, {"counter": counter})
        
        # Check max_iterations
        max_iter = step.loop_begin.max_iterations
        if max_iter > 0 and counter > max_iter:
            print(f"Warning: Loop '{loop_id}' exceeded max_iterations ({max_iter}), forcing exit")
            # Find the loop_end and skip to after it
            for idx in range(current_index + 1, len(self.workflow.steps)):
                end_step = self.workflow.steps[idx]
                if end_step.loop_end and end_step.loop_end.loop_id == loop_id:
                    return idx + 1  # Skip to after loop_end
            return len(self.workflow.steps)  # End of workflow if no loop_end found
        
        return current_index + 1  # Continue to loop body
    
    def _handle_loop_end(self, step: AOLStep, current_index: int, step_id_to_index: Dict[str, int]) -> int:
        """Handle loop_end marker - check exit condition and potentially loop back."""
        loop_id = step.loop_end.loop_id
        exit_when = step.loop_end.exit_when
        
        # Evaluate exit condition
        should_exit = self._evaluate_condition(exit_when)
        
        if should_exit:
            print(f"Loop '{loop_id}' exit condition met: {exit_when}")
            return current_index + 1  # Continue to next step after loop
        else:
            print(f"Loop '{loop_id}' continuing (exit_when: {exit_when} is false)")
            # Jump back to loop_begin
            return step_id_to_index[loop_id]
    
    def _handle_switch(self, step: AOLStep, current_index: int, step_id_to_index: Dict[str, int]) -> int:
        """Handle switch/case routing."""
        value = self._interpolate_string(step.switch.value)
        print(f"\n=== Switch on value: {value} ===")
        
        # Find matching case
        matched_steps = None
        for case in step.switch.cases:
            if value == case.match:
                matched_steps = case.steps
                break
        
        if matched_steps is None:
            matched_steps = step.switch.default or []
        
        if matched_steps:
            print(f"Matched steps: {matched_steps}")
            # For now, we'll just mark those steps as enabled
            # The actual steps will be executed in order
            # A more complex implementation would handle step jumping
        
        return current_index + 1
    
    def _handle_failure(self, step: AOLStep) -> bool:
        """
        Handle step failure according to on_failure strategy.
        
        Returns:
            True if execution should continue, False if should abort
        """
        if not step.on_failure:
            return False  # Default is abort
        
        strategy = step.on_failure.strategy
        
        if strategy == "abort":
            return False
        
        elif strategy == "skip":
            print(f"Skipping failed step '{step.id}' and continuing")
            return True
        
        elif strategy == "retry":
            max_retries = step.on_failure.max_retries or 3
            for attempt in range(max_retries):
                print(f"Retry {attempt + 1}/{max_retries} for step '{step.id}'")
                if self._execute_step(step):
                    return True
            print(f"All {max_retries} retries failed for step '{step.id}'")
            return False
        
        elif strategy == "fallback":
            fallback_id = step.on_failure.fallback_step
            if fallback_id:
                print(f"Falling back to step '{fallback_id}'")
                # Find and execute fallback step
                for s in self.workflow.steps:
                    if s.id == fallback_id:
                        return self._execute_step(s)
            return False
        
        elif strategy == "self_heal":
            print("Self-heal requested - preparing feedback for Planner")
            feedback = trigger_feedback_loop(
                step.id,
                step.description or "",
                {"context": self.context.get(step.id, {})},
                self.context
            )
            print(f"Feedback payload: {feedback}")
            # In a real system, this would trigger re-planning
            return False
        
        return False
    
    def _evaluate_condition(self, expression: str) -> bool:
        """
        Evaluate a condition expression.
        
        Supports:
        - "{{step.output}}" == "value"
        - "{{step.output}}" != "value"
        - "{{step.output}}" > "number" (numeric comparison)
        - "{{step.output}}" contains "substring"
        - not <expression>
        - <expr1> and <expr2>
        - <expr1> or <expr2>
        """
        # Interpolate all variables first
        interpolated = self._interpolate_string(expression)
        
        # Handle compound expressions (simple parsing)
        if " and " in interpolated:
            parts = interpolated.split(" and ", 1)
            return self._evaluate_simple_condition(parts[0]) and self._evaluate_simple_condition(parts[1])
        
        if " or " in interpolated:
            parts = interpolated.split(" or ", 1)
            return self._evaluate_simple_condition(parts[0]) or self._evaluate_simple_condition(parts[1])
        
        return self._evaluate_simple_condition(interpolated)
    
    def _evaluate_simple_condition(self, expr: str) -> bool:
        """Evaluate a simple condition without and/or."""
        expr = expr.strip()
        
        # Handle negation
        if expr.startswith("not "):
            return not self._evaluate_simple_condition(expr[4:])
        
        # Handle comparison operators
        for op in [" >= ", " <= ", " != ", " == ", " > ", " < ", " contains "]:
            if op in expr:
                left, right = expr.split(op, 1)
                left = left.strip().strip('"')
                right = right.strip().strip('"')
                
                if op == " == ":
                    return left == right
                elif op == " != ":
                    return left != right
                elif op == " contains ":
                    return right in left
                elif op in [" > ", " >= ", " < ", " <= "]:
                    try:
                        left_num = float(left)
                        right_num = float(right)
                        if op == " > ":
                            return left_num > right_num
                        elif op == " >= ":
                            return left_num >= right_num
                        elif op == " < ":
                            return left_num < right_num
                        elif op == " <= ":
                            return left_num <= right_num
                    except ValueError:
                        return False
                break
        
        # Boolean literals
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False
        
        # Truthy check (non-empty string)
        return bool(expr)
    
    def _interpolate_string(self, text: str) -> str:
        """
        Interpolate {{step_id.output_key}} variables in a string.
        """
        def replacer(match):
            ref = match.group(1)
            parts = ref.split(".", 1)
            if len(parts) != 2:
                return match.group(0)  # Return unchanged if invalid format
            
            step_id, key = parts
            
            if step_id in self.context and key in self.context[step_id]:
                value = self.context[step_id][key]
                return str(value).strip() if value else ""
            
            return match.group(0)  # Return unchanged if not found
        
        return re.sub(r'\{\{([^}]+)\}\}', replacer, text)
    
    def _interpolate_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively interpolate all string values in a dict."""
        result = {}
        for key, value in d.items():
            if isinstance(value, str):
                result[key] = self._interpolate_string(value)
            elif isinstance(value, dict):
                result[key] = self._interpolate_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._interpolate_string(v) if isinstance(v, str) else v 
                    for v in value
                ]
            else:
                result[key] = value
        return result


# Legacy Executor class for backwards compatibility
class Executor(ExecutorEngine):
    """Backwards-compatible Executor class."""
    
    def load_workflow(self, path: str) -> AOLWorkflow:
        """Load workflow from file (legacy method)."""
        return load_aol_file(path)
    
    def execute(self, workflow_path: str):
        """Execute workflow (legacy method)."""
        self.run_workflow(workflow_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PAWS Executor Engine")
    parser.add_argument("aol_path", help="Path to .aol file")
    parser.add_argument("--resume", action="store_true", help="Resume from last successful step")
    parser.add_argument("--log-dir", help="Directory for event logs", default="./.paws_logs")
    
    args = parser.parse_args()
    
    engine = ExecutorEngine(log_dir=args.log_dir)
    try:
        success = engine.run_workflow(args.aol_path, resume=args.resume)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
