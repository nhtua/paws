
import pytest
import yaml
from unittest.mock import patch, MagicMock
from paws.executor import Executor, ExecutorEngine
from paws.aol_parser import load_aol_file
from paws.core.models import AOLWorkflow

SAMPLE_WORKFLOW_YAML = """
provider:
  name: "Localhost"
user_inputs:
  prompt: "Test"
  resources: []
steps:
  - id: "step1"
    description: "Run command"
    extension: "Bash"
    inputs:
      command: "echo test"
    outputs: {}
"""

@pytest.fixture
def mock_registry():
    with patch("paws.executor.Registry") as MockRegistry:
        registry_instance = MockRegistry.return_value
        # Mock getting the extension definition
        mock_ext_def = MagicMock()
        mock_ext_def.source = "paws.extensions.bash"
        mock_ext_def.name = "Bash"
        registry_instance.get_extension.return_value = mock_ext_def
        registry_instance.discover_extensions.return_value = [mock_ext_def]
        yield registry_instance

def test_executor_load_workflow_success(tmp_path):
    executor = Executor()
    f = tmp_path / "test.aol"
    f.write_text(SAMPLE_WORKFLOW_YAML)
    
    workflow = executor.load_workflow(str(f))
    assert isinstance(workflow, AOLWorkflow)
    assert workflow.steps[0].id == "step1"

def test_executor_load_workflow_failure():
    executor = Executor()
    # No file created - should raise ValueError with "not found" message
    with pytest.raises(ValueError, match="AOL file not found"):
        executor.load_workflow("nonexistent.aol")

@patch("paws.mcp_client.importlib.import_module")
def test_executor_execute_success(mock_import, mock_registry, tmp_path):
    # Setup mock extension instance
    mock_module = MagicMock()
    mock_ext_instance = MagicMock()
    mock_module.extension_instance = mock_ext_instance
    mock_import.return_value = mock_module
    
    # Mock successful tool call result
    mock_ext_instance.call_tool.return_value = {
        "isError": False, 
        "content": [{"type": "text", "text": "Success"}]
    }
    
    executor = Executor(log_dir=str(tmp_path / "logs"))
    f = tmp_path / "run.aol"
    f.write_text(SAMPLE_WORKFLOW_YAML)
    
    # Run execute
    executor.execute(str(f))
    
    # Verify tool was called
    mock_ext_instance.call_tool.assert_called_once()
    # args[0] is name, args[1] is inputs
    call_args = mock_ext_instance.call_tool.call_args
    assert call_args[0][0] == "execute_command"
    assert call_args[0][1] == {"command": "echo test"}

@patch("paws.mcp_client.importlib.import_module")
def test_executor_execute_unknown_extension(mock_import, mock_registry, tmp_path):
    # Setup registry to return None for extension
    mock_registry.get_extension.return_value = None
    
    executor = Executor(log_dir=str(tmp_path / "logs"))
    f = tmp_path / "unknown.aol"
    f.write_text(SAMPLE_WORKFLOW_YAML)
    
    # Execute should fail gracefully (return False)
    result = executor.run_workflow(str(f))
    assert result == False
    
    # Import should not be called if extension not found
    mock_import.assert_not_called()

@patch("paws.mcp_client.importlib.import_module")
def test_executor_execute_tool_failure(mock_import, mock_registry, tmp_path):
    # Setup mock extension instance to return error
    mock_module = MagicMock()
    mock_ext_instance = MagicMock()
    mock_module.extension_instance = mock_ext_instance
    mock_import.return_value = mock_module
    
    mock_ext_instance.call_tool.return_value = {
        "isError": True, 
        "content": [{"type": "text", "text": "Failed"}]
    }
    
    executor = Executor(log_dir=str(tmp_path / "logs"))
    f = tmp_path / "fail.aol"
    f.write_text(SAMPLE_WORKFLOW_YAML)
    
    # Execute should return False on failure
    result = executor.run_workflow(str(f))
    assert result == False
    
    # Should still try to call the tool
    mock_ext_instance.call_tool.assert_called_once()


# New tests for AOL v1.0 features

def test_variable_interpolation(tmp_path):
    """Test that variable interpolation works correctly."""
    engine = ExecutorEngine(log_dir=str(tmp_path / "logs"))
    
    # Set up context
    engine.context["step_1"] = {"stdout": "hello world", "exit_code": "0"}
    engine.context["user_inputs"] = {"prompt": "test prompt"}
    
    # Test simple interpolation
    result = engine._interpolate_string("Value is {{step_1.stdout}}")
    assert result == "Value is hello world"
    
    # Test multiple interpolations
    result = engine._interpolate_string("{{step_1.stdout}} and {{step_1.exit_code}}")
    assert result == "hello world and 0"
    
    # Test user_inputs interpolation
    result = engine._interpolate_string("Prompt: {{user_inputs.prompt}}")
    assert result == "Prompt: test prompt"

def test_condition_evaluation(tmp_path):
    """Test condition expression evaluation."""
    engine = ExecutorEngine(log_dir=str(tmp_path / "logs"))
    engine.context["check"] = {"stdout": "success", "code": "0"}
    
    # Test equality
    assert engine._evaluate_condition('"{{check.stdout}}" == "success"') == True
    assert engine._evaluate_condition('"{{check.stdout}}" == "failure"') == False
    
    # Test inequality
    assert engine._evaluate_condition('"{{check.stdout}}" != "failure"') == True
    
    # Test contains
    assert engine._evaluate_condition('"{{check.stdout}}" contains "suc"') == True
    
    # Test numeric comparison
    engine.context["num"] = {"count": "5"}
    assert engine._evaluate_condition('"{{num.count}}" >= "3"') == True
    assert engine._evaluate_condition('"{{num.count}}" < "10"') == True

def test_loop_counter(tmp_path):
    """Test loop counter management."""
    engine = ExecutorEngine(log_dir=str(tmp_path / "logs"))
    
    # Simulate loop iteration
    engine.loop_counters["my_loop"] = 0
    engine.loop_counters["my_loop"] += 1
    engine.context["my_loop"] = {"counter": str(engine.loop_counters["my_loop"])}
    
    assert engine.context["my_loop"]["counter"] == "1"
    
    # Interpolate counter
    result = engine._interpolate_string("Iteration {{my_loop.counter}}")
    assert result == "Iteration 1"
