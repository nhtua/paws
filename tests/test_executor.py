
import pytest
import yaml
from unittest.mock import patch, MagicMock
from paws.executor import Executor
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
    # No file created
    with pytest.raises(ValueError, match="Failed to load AOL workflow"):
        executor.load_workflow("nonexistent.aol")

@patch("paws.executor.importlib.import_module")
def test_executor_execute_success(mock_import, mock_registry, tmp_path):
    # Setup mock extension instance
    mock_module = MagicMock()
    mock_ext_instance = MagicMock()
    mock_module.extension_instance = mock_ext_instance
    mock_import.return_value = mock_module
    
    # Mock successful tool call result
    mock_ext_instance.call_tool.return_value = {"isError": False, "content": "Success"}
    
    executor = Executor()
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

@patch("paws.executor.importlib.import_module")
def test_executor_execute_unknown_extension(mock_import, mock_registry, tmp_path):
    # Setup registry to return None for extension
    mock_registry.get_extension.return_value = None
    
    executor = Executor()
    f = tmp_path / "unknown.aol"
    f.write_text(SAMPLE_WORKFLOW_YAML)
    
    executor.execute(str(f))
    
    # Import should not be called if extension not found
    mock_import.assert_not_called()

@patch("paws.executor.importlib.import_module")
def test_executor_execute_tool_failure(mock_import, mock_registry, tmp_path):
    # Setup mock extension instance to return error
    mock_module = MagicMock()
    mock_ext_instance = MagicMock()
    mock_module.extension_instance = mock_ext_instance
    mock_import.return_value = mock_module
    
    mock_ext_instance.call_tool.return_value = {"isError": True, "content": "Failed"}
    
    executor = Executor()
    f = tmp_path / "fail.aol"
    f.write_text(SAMPLE_WORKFLOW_YAML)
    
    executor.execute(str(f))
    
    # Should still try to call the tool
    mock_ext_instance.call_tool.assert_called_once()
