
import pytest
from unittest.mock import patch, MagicMock
from paws.extensions.bash import BashExtension

@pytest.fixture
def bash_extension():
    return BashExtension()

def test_get_tool_definition(bash_extension):
    tool_def = bash_extension.get_tool_definition()
    assert tool_def["name"] == "execute_command"
    assert "command" in tool_def["inputSchema"]["properties"]

def test_call_tool_unknown_name(bash_extension):
    with pytest.raises(ValueError, match="Unknown tool"):
        bash_extension.call_tool("unknown_tool", {})

def test_call_tool_missing_command(bash_extension):
    with pytest.raises(ValueError, match="Missing 'command' argument"):
        bash_extension.call_tool("execute_command", {})

@patch("subprocess.run")
def test_call_tool_success(mock_run, bash_extension):
    mock_run.return_value = MagicMock(returncode=0, stdout="success output", stderr="")
    
    result = bash_extension.call_tool("execute_command", {"command": "echo hello"})
    
    assert result["isError"] is False
    assert result["content"][0]["text"] == "success output"
    mock_run.assert_called_once()

@patch("subprocess.run")
def test_call_tool_failure(mock_run, bash_extension):
    # Simulate a command failure
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error message")
    
    result = bash_extension.call_tool("execute_command", {"command": "bad_command"})
    
    assert result["isError"] is True
    assert "Error (Exit Code 1)" in result["content"][0]["text"]
    assert "error message" in result["content"][0]["text"]

@patch("subprocess.run")
def test_call_tool_exception(mock_run, bash_extension):
    # Simulate an exception during subprocess.run
    mock_run.side_effect = Exception("Major fail")
    
    result = bash_extension.call_tool("execute_command", {"command": "whatever"})
    
    assert result["isError"] is True
    assert "Major fail" in result["content"][0]["text"]
