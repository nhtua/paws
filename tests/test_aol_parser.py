"""Tests for the AOL Parser module."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from paws.aol_parser import (
    load_aol_file, 
    validate_dependencies, 
    extract_variable_references,
    _validate_loop_structure
)
from paws.core.models import AOLWorkflow, AOLStep, AOLLoopBegin, AOLLoopEnd
from paws.core.registry import Registry


# --- Valid workflow for testing ---
VALID_WORKFLOW = """
provider:
  name: Localhost
  context:
    workspace: /tmp/test
  entitlements:
    - scope: "Read/Write ./workspace/"
      capability: "Execute Bash Commands"

user_inputs:
  prompt: "Test workflow"
  resources:
    - ./input.txt

steps:
  - id: step_1
    description: First step
    extension: Bash
    inputs:
      command: "echo hello"
    outputs:
      stdout: "Greeting"
"""

WORKFLOW_WITH_LOOP = """
provider:
  name: Localhost

user_inputs:
  prompt: "Loop test"

steps:
  - id: my_loop
    loop_begin:
      max_iterations: 5

  - id: do_work
    description: Work step
    extension: Bash
    inputs:
      command: "echo iteration {{my_loop.counter}}"

  - id: my_loop_end
    loop_end:
      loop_id: my_loop
      exit_when: '"{{my_loop.counter}}" >= "5"'
"""


INVALID_LOOP_WORKFLOW = """
provider:
  name: Localhost

user_inputs:
  prompt: "Bad loop"

steps:
  - id: loop_end_first
    loop_end:
      loop_id: nonexistent_loop
      exit_when: "true"
"""


class TestLoadAolFile:
    def test_load_valid_file(self, tmp_path):
        f = tmp_path / "test.aol"
        f.write_text(VALID_WORKFLOW)
        
        workflow = load_aol_file(str(f))
        
        assert isinstance(workflow, AOLWorkflow)
        assert workflow.provider.name == "Localhost"
        assert workflow.user_inputs.prompt == "Test workflow"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].id == "step_1"
    
    def test_file_not_found(self):
        with pytest.raises(ValueError, match="AOL file not found"):
            load_aol_file("nonexistent.aol")
    
    def test_wrong_extension(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text(VALID_WORKFLOW)
        
        with pytest.raises(ValueError, match="Expected .aol file"):
            load_aol_file(str(f))
    
    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.aol"
        f.write_text("")
        
        with pytest.raises(ValueError, match="Empty AOL file"):
            load_aol_file(str(f))
    
    def test_invalid_yaml(self, tmp_path):
        f = tmp_path / "bad.aol"
        f.write_text("{ invalid yaml : : }")
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            load_aol_file(str(f))
    
    def test_schema_validation_error(self, tmp_path):
        """Test that missing required fields raise ValidationError."""
        f = tmp_path / "missing.aol"
        f.write_text("provider:\n  name: Test\n")  # Missing user_inputs and steps
        
        with pytest.raises(ValidationError):
            load_aol_file(str(f))


class TestValidateDependencies:
    def test_valid_dependencies(self, tmp_path):
        f = tmp_path / "test.aol"
        f.write_text(VALID_WORKFLOW)
        workflow = load_aol_file(str(f))
        
        registry = Registry()  # Has Bash by default
        is_valid, errors = validate_dependencies(workflow, registry)
        
        assert is_valid == True
        assert errors == []
    
    def test_missing_extension(self, tmp_path):
        workflow_yaml = """
provider:
  name: Localhost
user_inputs:
  prompt: "Test"
steps:
  - id: s1
    extension: NonExistentExtension
    inputs: {}
"""
        f = tmp_path / "missing_ext.aol"
        f.write_text(workflow_yaml)
        workflow = load_aol_file(str(f))
        
        registry = Registry()
        is_valid, errors = validate_dependencies(workflow, registry)
        
        assert is_valid == False
        assert "Extension 'NonExistentExtension' not found" in errors[0]
    
    def test_valid_loop_structure(self, tmp_path):
        f = tmp_path / "loop.aol"
        f.write_text(WORKFLOW_WITH_LOOP)
        workflow = load_aol_file(str(f))
        
        registry = Registry()
        is_valid, errors = validate_dependencies(workflow, registry)
        
        assert is_valid == True
    
    def test_invalid_loop_reference(self, tmp_path):
        f = tmp_path / "bad_loop.aol"
        f.write_text(INVALID_LOOP_WORKFLOW)
        workflow = load_aol_file(str(f))
        
        registry = Registry()
        is_valid, errors = validate_dependencies(workflow, registry)
        
        assert is_valid == False
        assert any("nonexistent_loop" in e for e in errors)


class TestExtractVariableReferences:
    def test_simple_reference(self):
        refs = extract_variable_references("Value: {{step_1.stdout}}")
        assert refs == ["step_1.stdout"]
    
    def test_multiple_references(self):
        refs = extract_variable_references("{{a.x}} and {{b.y}}")
        assert refs == ["a.x", "b.y"]
    
    def test_no_references(self):
        refs = extract_variable_references("No variables here")
        assert refs == []
    
    def test_user_inputs_reference(self):
        refs = extract_variable_references("Prompt: {{user_inputs.prompt}}")
        assert refs == ["user_inputs.prompt"]


class TestValidateLoopStructure:
    def test_properly_nested_loops(self):
        steps = [
            AOLStep(id="outer", loop_begin=AOLLoopBegin()),
            AOLStep(id="inner", loop_begin=AOLLoopBegin()),
            AOLStep(id="inner_end", loop_end=AOLLoopEnd(loop_id="inner", exit_when="true")),
            AOLStep(id="outer_end", loop_end=AOLLoopEnd(loop_id="outer", exit_when="true")),
        ]
        
        errors = _validate_loop_structure(steps)
        assert errors == []
    
    def test_improperly_nested_loops(self):
        """Test that interleaved loops are detected."""
        steps = [
            AOLStep(id="outer", loop_begin=AOLLoopBegin()),
            AOLStep(id="inner", loop_begin=AOLLoopBegin()),
            # Wrong order - outer ends before inner
            AOLStep(id="outer_end", loop_end=AOLLoopEnd(loop_id="outer", exit_when="true")),
            AOLStep(id="inner_end", loop_end=AOLLoopEnd(loop_id="inner", exit_when="true")),
        ]
        
        errors = _validate_loop_structure(steps)
        assert len(errors) > 0
        assert "invalid nesting" in errors[0]
    
    def test_unclosed_loop(self):
        steps = [
            AOLStep(id="my_loop", loop_begin=AOLLoopBegin()),
            AOLStep(id="work", extension="Bash", inputs={"command": "echo hi"}),
            # Missing loop_end
        ]
        
        errors = _validate_loop_structure(steps)
        assert len(errors) == 1
        assert "never closed" in errors[0]
