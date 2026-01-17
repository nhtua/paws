
import pytest
from unittest.mock import patch, MagicMock
from paws.extensions.bash import BashExtension

@pytest.fixture
def bash_extension():
    return BashExtension()

@patch("subprocess.run")
def test_call_tool_partial_failure_with_stderr(mock_run, bash_extension):
    # Simulate a command success (exit code 0) but with stderr content (e.g. pipe masking)
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="hidden error")
    
    result = bash_extension.call_tool("execute_command", {"command": "cmd1 | cmd2"})
    
    assert result["isError"] is False
    assert "--- stderr ---" in result["content"][0]["text"]
    assert "hidden error" in result["content"][0]["text"]
