"""
Validator - Semantic Validation (The Critic)

Implements the Evaluator-Optimizer pattern. Checks if a step actually succeeded
rather than just assuming it did because the code didn't crash.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from paws.mcp_client import ExecutionResult


def validate_step(
    step_output: ExecutionResult,
    expected_outputs: Dict[str, Any],
    step_id: str
) -> tuple[bool, List[str]]:
    """
    Perform semantic checks on step output.
    
    Validation includes:
    - Step didn't error
    - Expected output files exist (if file paths in outputs)
    - Output is non-empty (if required)
    
    Args:
        step_output: The ExecutionResult from step execution
        expected_outputs: The outputs dict from the step definition
        step_id: ID of the step for error messages
        
    Returns:
        Tuple of (is_valid, list of validation errors)
    """
    errors = []
    
    # Check for execution error
    if step_output.is_error:
        errors.append(f"Step '{step_id}' returned error: {step_output.stderr or step_output.stdout}")
    
    # Check expected outputs exist
    for output_key, output_desc in expected_outputs.items():
        # Check if this is a file output that should exist
        if _is_file_output(output_key, output_desc):
            # Try to find the file path in the result
            file_path = _extract_file_path(step_output, output_key)
            if file_path:
                if not Path(file_path).exists():
                    errors.append(f"Step '{step_id}': expected output file '{file_path}' does not exist")
                elif Path(file_path).stat().st_size == 0:
                    errors.append(f"Step '{step_id}': output file '{file_path}' is empty")
    
    # Check stdout is not empty if we expected stdout output
    if "stdout" in expected_outputs:
        if not step_output.stdout.strip():
            # This is a warning, not necessarily an error
            pass  # Could add to warnings list if needed
    
    return (len(errors) == 0, errors)


def validate_outputs_exist(context: Dict[str, Dict[str, Any]], references: List[str]) -> tuple[bool, List[str]]:
    """
    Validate that all variable references can be resolved.
    
    Args:
        context: Current execution context mapping step_id -> outputs
        references: List of references like 'step_1.stdout'
        
    Returns:
        Tuple of (is_valid, list of unresolvable references)
    """
    errors = []
    
    for ref in references:
        parts = ref.split(".", 1)
        if len(parts) != 2:
            errors.append(f"Invalid reference format: '{ref}'")
            continue
        
        step_id, output_key = parts
        
        # Check special references
        if step_id in ("user_inputs", "provider"):
            continue  # These are always available
        
        if step_id not in context:
            errors.append(f"Step '{step_id}' not found in context for reference '{ref}'")
        elif output_key not in context[step_id]:
            errors.append(f"Output '{output_key}' not found in step '{step_id}' for reference '{ref}'")
    
    return (len(errors) == 0, errors)


def trigger_feedback_loop(
    step_id: str,
    step_description: str,
    error_log: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Prepare data to send back to the Planner for re-planning.
    
    This creates a structured payload that the Planner can use to
    understand what went wrong and generate a corrected AOL file.
    
    Args:
        step_id: The failing step ID
        step_description: What the step was trying to do
        error_log: Error information from the failed step
        context: Current execution context
        
    Returns:
        Payload for Planner re-planning request
    """
    return {
        "type": "self_heal_request",
        "failed_step": {
            "id": step_id,
            "description": step_description
        },
        "error": error_log,
        "context_summary": {
            "completed_steps": list(context.keys()),
            "last_outputs": _summarize_context(context)
        },
        "request": "Please analyze the failure and generate a corrected workflow plan."
    }


def _is_file_output(output_key: str, output_desc: Any) -> bool:
    """Heuristic to determine if an output is expected to be a file."""
    key_lower = output_key.lower()
    
    # Common file output patterns
    file_indicators = ["file", "path", "output_file", "result_file", "image", "video", "audio", "pdf"]
    if any(ind in key_lower for ind in file_indicators):
        return True
    
    # Check description
    if isinstance(output_desc, str):
        desc_lower = output_desc.lower()
        if any(ind in desc_lower for ind in file_indicators):
            return True
    
    return False


def _extract_file_path(result: ExecutionResult, output_key: str) -> Optional[str]:
    """Try to extract a file path from the result."""
    # Check in structured result
    if output_key in result.result:
        value = result.result[output_key]
        if isinstance(value, str) and ("/" in value or "\\" in value):
            return value
    
    # Check stdout for file paths
    stdout = result.stdout.strip()
    if stdout and ("/" in stdout or "\\" in stdout):
        # Simple heuristic: take the last line as potential path
        lines = stdout.split("\n")
        potential_path = lines[-1].strip()
        if potential_path and not potential_path.startswith("#"):
            return potential_path
    
    return None


def _summarize_context(context: Dict[str, Any]) -> Dict[str, str]:
    """Create a summary of context for feedback loop."""
    summary = {}
    for step_id, outputs in context.items():
        if isinstance(outputs, dict):
            # Just include stdout summary
            stdout = outputs.get("stdout", "")
            if stdout:
                summary[step_id] = stdout[:100] + "..." if len(stdout) > 100 else stdout
    return summary
