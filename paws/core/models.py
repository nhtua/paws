"""
AOL v1.0 Pydantic Models

Defines the data structures for Autonomous Operator Language workflows
according to the AOL v1.0 Specification.
"""

from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, ConfigDict


# --- Provider Section ---

class AOLEntitlement(BaseModel):
    """Access control rule for the workflow."""
    scope: str = Field(..., description="Resource scope (e.g., 'Read/Write ./workspace/')")
    capability: str = Field(..., description="Allowed action (e.g., 'Execute Bash Commands')")
    
    model_config = ConfigDict(extra="forbid")


class AOLProvider(BaseModel):
    """Provider configuration for the workflow session."""
    name: str = Field(..., description="Provider identifier (e.g., 'Localhost')")
    context: Dict[str, Any] = Field(default_factory=dict, description="Environment/auth context")
    entitlements: List[AOLEntitlement] = Field(default_factory=list, description="Access control rules")
    
    model_config = ConfigDict(extra="forbid")


# --- User Inputs Section ---

class AOLUserInputs(BaseModel):
    """Initial state (State Zero) for the workflow."""
    prompt: str = Field(..., description="The original user prompt")
    resources: List[str] = Field(default_factory=list, description="Initial file paths or URIs")
    
    model_config = ConfigDict(extra="forbid")


# --- Control Flow Constructs ---

class AOLCondition(BaseModel):
    """Conditional execution - step runs only if expression is true."""
    if_: str = Field(..., alias="if", description="Boolean expression to evaluate")
    
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class AOLOnFailure(BaseModel):
    """Error handling strategy for a step."""
    strategy: Literal["abort", "retry", "skip", "fallback", "self_heal"] = Field(
        ..., description="How to handle failure"
    )
    max_retries: Optional[int] = Field(None, description="Max retry attempts (for 'retry' strategy)")
    fallback_step: Optional[str] = Field(None, description="Step to execute (for 'fallback' strategy)")
    
    model_config = ConfigDict(extra="forbid")


class AOLLoopBegin(BaseModel):
    """Loop start marker with built-in counter."""
    max_iterations: int = Field(100, description="Maximum iterations before forced exit (0 = no limit)")
    
    model_config = ConfigDict(extra="forbid")


class AOLLoopEnd(BaseModel):
    """Loop end marker with exit condition."""
    loop_id: str = Field(..., description="ID of the corresponding loop_begin step")
    exit_when: str = Field(..., description="Boolean expression; when true, exit the loop")
    
    model_config = ConfigDict(extra="forbid")


class AOLSwitchCase(BaseModel):
    """A case branch in a switch statement."""
    match: str = Field(..., description="Literal value to match")
    steps: List[str] = Field(..., description="Step IDs to execute if matched")
    
    model_config = ConfigDict(extra="forbid")


class AOLSwitch(BaseModel):
    """Switch/case for multi-branch decisions."""
    value: str = Field(..., description="Value expression to match against")
    cases: List[AOLSwitchCase] = Field(..., description="List of case branches")
    default: Optional[List[str]] = Field(None, description="Steps if no match")
    
    model_config = ConfigDict(extra="forbid")


# --- Step Definition ---

class AOLStep(BaseModel):
    """A single step in the workflow."""
    id: str = Field(..., description="Unique step identifier")
    description: Optional[str] = Field(None, description="Human-readable description")
    extension: Optional[str] = Field(None, description="Extension to invoke (not required for loop/switch markers)")
    tool: Optional[str] = Field(None, description="Specific tool within the extension")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Expected output schema")
    condition: Optional[AOLCondition] = Field(None, description="Conditional execution")
    on_failure: Optional[AOLOnFailure] = Field(None, description="Error handling strategy")
    timeout: Optional[str] = Field(None, description="Maximum execution time (e.g., '30s', '5m')")
    loop_begin: Optional[AOLLoopBegin] = Field(None, description="Loop start marker")
    loop_end: Optional[AOLLoopEnd] = Field(None, description="Loop end marker")
    switch: Optional[AOLSwitch] = Field(None, description="Switch/case routing")
    
    model_config = ConfigDict(extra="forbid")


# --- Extension Definition (for Registry) ---

class AOLExtension(BaseModel):
    """Extension registration info."""
    name: str = Field(..., description="Name of the extension, e.g., 'Bash'")
    source: Optional[str] = Field(None, description="Source URI or path to the extension module")
    
    model_config = ConfigDict(extra="forbid")


# --- Complete Workflow ---

class AOLWorkflow(BaseModel):
    """Complete AOL workflow document."""
    provider: AOLProvider
    user_inputs: AOLUserInputs
    steps: List[AOLStep]
    
    model_config = ConfigDict(extra="forbid")
