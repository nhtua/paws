
import pytest
from pydantic import ValidationError
from paws.core.models import AOLWorkflow, AOLProvider, AOLUserInputs, AOLStep, AOLExtension

def test_aol_provider_valid():
    provider = AOLProvider(name="Localhost", context={"auth": "token"})
    assert provider.name == "Localhost"
    assert provider.context == {"auth": "token"}

def test_aol_provider_invalid_extra_field():
    with pytest.raises(ValidationError):
        AOLProvider(name="Localhost", extra_field="fail")

def test_aol_user_inputs_valid():
    inputs = AOLUserInputs(prompt="do something", resources=["file.txt"])
    assert inputs.prompt == "do something"
    assert inputs.resources == ["file.txt"]

def test_aol_extension_valid():
    ext = AOLExtension(name="Bash", source="paws.extensions.bash")
    assert ext.name == "Bash"
    assert ext.source == "paws.extensions.bash"

def test_aol_step_valid():
    step = AOLStep(
        id="step_1",
        description="Run command",
        extension="Bash",
        inputs={"command": "ls"},
        outputs={"stdout": "output"}
    )
    assert step.id == "step_1"
    assert step.extension == "Bash"

def test_aol_workflow_valid():
    workflow = AOLWorkflow(
        provider=AOLProvider(name="Localhost"),
        user_inputs=AOLUserInputs(prompt="hello"),
        steps=[
            AOLStep(
                id="1", description="desc", extension="Bash", 
                inputs={"c": "d"}, outputs={}
            )
        ]
    )
    assert workflow.provider.name == "Localhost"
    assert len(workflow.steps) == 1
