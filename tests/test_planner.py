
import pytest
import json
from unittest.mock import patch, MagicMock
from paws.planner import Planner
from paws.core.models import AOLWorkflow

# Sample valid JSON response mimicking what Gemini would return
VALID_AOL_JSON = json.dumps({
    "provider": {"name": "Localhost", "context": {}},
    "user_inputs": {"prompt": "test prompt", "resources": []},
    "steps": [
        {
            "id": "s1",
            "description": "d1",
            "extension": "Bash",
            "inputs": {"command": "echo hi"},
            "outputs": {}
        }
    ]
})

@pytest.fixture
def mock_genai_client():
    with patch("paws.planner.genai.Client") as mock:
        yield mock

def test_planner_init(mock_genai_client):
    planner = Planner(api_key="fake_key")
    assert planner.client is not None

def test_planner_plan_success(mock_genai_client):
    # Setup mock response
    mock_instance = mock_genai_client.return_value
    mock_response = MagicMock()
    mock_response.text = VALID_AOL_JSON
    mock_instance.models.generate_content.return_value = mock_response

    planner = Planner(api_key="fake_key")
    workflow = planner.plan("test prompt")
    
    assert isinstance(workflow, AOLWorkflow)
    assert workflow.user_inputs.prompt == "test prompt"
    assert len(workflow.steps) == 1
    assert workflow.steps[0].id == "s1"

def test_planner_plan_empty_response(mock_genai_client):
    mock_instance = mock_genai_client.return_value
    mock_response = MagicMock()
    mock_response.text = "" # Empty response
    mock_instance.models.generate_content.return_value = mock_response

    planner = Planner(api_key="fake_key")
    
    with pytest.raises(ValueError, match="Empty response from Gemini"):
        planner.plan("test prompt")

def test_planner_plan_invalid_json(mock_genai_client):
    mock_instance = mock_genai_client.return_value
    mock_response = MagicMock()
    mock_response.text = "{ invalid json"
    mock_instance.models.generate_content.return_value = mock_response

    planner = Planner(api_key="fake_key")
    
    with pytest.raises(ValueError, match="Failed to parse AOLWorkflow"):
        planner.plan("test prompt")

def test_get_system_prompt_includes_bash(mock_genai_client):
    # This tests that _get_system_prompt correctly loads available extensions
    planner = Planner(api_key="fake_key")
    prompt = planner._get_system_prompt()
    assert "You are the PAWS Planner" in prompt
    assert "Extension 'Bash'" in prompt
    assert "execute_command" in prompt
