
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class AOLProvider(BaseModel):
    name: str = Field(..., description="Name of the provider, e.g., 'Localhost'")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context for the provider, e.g., auth credentials")
    
    model_config = ConfigDict(extra="forbid")

class AOLUserInputs(BaseModel):
    prompt: str = Field(..., description="The original user prompt")
    resources: List[str] = Field(default_factory=list, description="List of file paths or resources")
    
    model_config = ConfigDict(extra="forbid")

class AOLExtension(BaseModel):
    name: str = Field(..., description="Name of the extension, e.g., 'Bash'")
    source: Optional[str] = Field(None, description="Source URI or path to the extension definition")
    
    model_config = ConfigDict(extra="forbid")

class AOLStep(BaseModel):
    id: str = Field(..., description="Unique ID for the step")
    description: str = Field(..., description="Human-readable description of the step")
    extension: str = Field(..., description="Name of the extension to use")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input parameters for the tool")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Expected output keys and descriptions")
    
    model_config = ConfigDict(extra="forbid")

class AOLWorkflow(BaseModel):
    provider: AOLProvider
    user_inputs: AOLUserInputs
    steps: List[AOLStep]
    
    model_config = ConfigDict(extra="forbid")
