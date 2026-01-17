"""
AOL Parser - The Loader

Reads AOL YAML files and validates them against the Pydantic schema.
This is the "front-end" of the executor that converts YAML to structured objects.
"""

from pathlib import Path
from typing import Set, List, Tuple
import re
import yaml

from paws.core.models import AOLWorkflow, AOLStep
from paws.core.registry import Registry


def load_aol_file(file_path: str) -> AOLWorkflow:
    """
    Read the raw .aol YAML file and parse into a validated WorkflowPlan.
    
    Args:
        file_path: Path to the .aol file
        
    Returns:
        Validated AOLWorkflow object
        
    Raises:
        ValueError: If file cannot be read or parsed
        ValidationError: If YAML doesn't match AOL schema
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"AOL file not found: {file_path}")
    
    if not path.suffix == ".aol":
        raise ValueError(f"Expected .aol file, got: {path.suffix}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {file_path}: {e}")
    
    if data is None:
        raise ValueError(f"Empty AOL file: {file_path}")
    
    # Validate against Pydantic schema
    return AOLWorkflow(**data)


def validate_dependencies(workflow: AOLWorkflow, registry: Registry) -> Tuple[bool, List[str]]:
    """
    Check that all required extensions exist before starting execution.
    
    Args:
        workflow: The parsed AOL workflow
        registry: Extension registry to check against
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Collect all extensions used in steps
    required_extensions: Set[str] = set()
    for step in workflow.steps:
        if step.extension:
            required_extensions.add(step.extension)
    
    # Check each extension exists in registry
    for ext_name in required_extensions:
        if not registry.get_extension(ext_name):
            errors.append(f"Extension '{ext_name}' not found in registry")
    
    # Validate step references (for loops and conditions)
    step_ids = {step.id for step in workflow.steps}
    errors.extend(_validate_step_references(workflow.steps, step_ids))
    
    # Validate loop structure
    errors.extend(_validate_loop_structure(workflow.steps))
    
    return (len(errors) == 0, errors)


def _validate_step_references(steps: List[AOLStep], step_ids: Set[str]) -> List[str]:
    """Validate that all step references point to existing steps."""
    errors = []
    
    for step in steps:
        # Check loop_end references
        if step.loop_end:
            if step.loop_end.loop_id not in step_ids:
                errors.append(f"Step '{step.id}': loop_end references unknown loop_id '{step.loop_end.loop_id}'")
        
        # Check switch case step references  
        if step.switch:
            for case in step.switch.cases:
                for ref_id in case.steps:
                    if ref_id not in step_ids:
                        errors.append(f"Step '{step.id}': switch case references unknown step '{ref_id}'")
            if step.switch.default:
                for ref_id in step.switch.default:
                    if ref_id not in step_ids:
                        errors.append(f"Step '{step.id}': switch default references unknown step '{ref_id}'")
        
        # Check fallback step references
        if step.on_failure and step.on_failure.fallback_step:
            if step.on_failure.fallback_step not in step_ids:
                errors.append(f"Step '{step.id}': fallback_step references unknown step '{step.on_failure.fallback_step}'")
    
    return errors


def _validate_loop_structure(steps: List[AOLStep]) -> List[str]:
    """Validate that loops are properly structured (matched begin/end, no interleaving)."""
    errors = []
    loop_stack = []  # Stack of (loop_id, step_index)
    loop_begins = {}  # loop_id -> step_index
    
    for idx, step in enumerate(steps):
        if step.loop_begin:
            loop_stack.append((step.id, idx))
            loop_begins[step.id] = idx
        
        if step.loop_end:
            loop_id = step.loop_end.loop_id
            
            # Check that the referenced loop_begin exists
            if loop_id not in loop_begins:
                errors.append(f"Step '{step.id}': loop_end references '{loop_id}' but no loop_begin found")
                continue
            
            # Check that loop_end comes after loop_begin
            if loop_begins[loop_id] >= idx:
                errors.append(f"Step '{step.id}': loop_end must come after loop_begin '{loop_id}'")
                continue
            
            # Check proper nesting (innermost loop must end first)
            if loop_stack:
                expected_loop_id, _ = loop_stack[-1]
                if loop_id != expected_loop_id:
                    errors.append(f"Step '{step.id}': expected loop_end for '{expected_loop_id}', got '{loop_id}' (invalid nesting)")
                else:
                    loop_stack.pop()
    
    # Check for unclosed loops
    for loop_id, idx in loop_stack:
        errors.append(f"Loop '{loop_id}' (step index {idx}) is never closed with loop_end")
    
    return errors


def extract_variable_references(text: str) -> List[str]:
    """
    Extract all variable references from a string.
    
    Args:
        text: String potentially containing {{step_id.output}} references
        
    Returns:
        List of variable references (e.g., ['step_1.stdout', 'get_date.result'])
    """
    pattern = r'\{\{([^}]+)\}\}'
    return re.findall(pattern, text)
