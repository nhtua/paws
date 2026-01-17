"""
MCP Client - Agent-Computer Interface Translation Layer

Isolates the Executor from the messy details of CLI commands.
Treats tools as "Black Boxes" via the Model Context Protocol (MCP) pattern.
"""

import importlib
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from paws.core.models import AOLExtension
from paws.core.registry import Registry


@dataclass
class ExecutionResult:
    """Standardized result from tool execution."""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    result: Dict[str, Any] = field(default_factory=dict)
    is_error: bool = False
    
    def to_context(self) -> Dict[str, Any]:
        """Convert to context dict for variable interpolation."""
        return {
            "stdout": self.stdout.strip(),
            "stderr": self.stderr.strip(),
            "exit_code": str(self.exit_code),
            "result": self.result,
            "is_error": self.is_error
        }


def discover_tools(registry: Registry) -> Dict[str, Dict[str, Any]]:
    """
    Scan for available MCP servers (Extensions) and load their capability schemas.
    
    Args:
        registry: Extension registry to scan
        
    Returns:
        Dict mapping extension names to their tool definitions
    """
    tools = {}
    
    for ext in registry.discover_extensions():
        try:
            module = importlib.import_module(ext.source)
            instance = getattr(module, 'extension_instance', None)
            if instance and hasattr(instance, 'get_tool_definition'):
                tools[ext.name] = instance.get_tool_definition()
        except Exception as e:
            # Log but don't fail - some extensions might not be available
            print(f"Warning: Could not load extension '{ext.name}': {e}")
    
    return tools


def load_extension_instance(extension: AOLExtension) -> Any:
    """
    Load the extension instance from its source module.
    
    Args:
        extension: Extension definition with source path
        
    Returns:
        The extension_instance object
        
    Raises:
        ValueError: If extension cannot be loaded
    """
    if not extension.source:
        raise ValueError(f"Extension '{extension.name}' has no source defined")
    
    try:
        module = importlib.import_module(extension.source)
        instance = getattr(module, 'extension_instance', None)
        if instance is None:
            raise ValueError(f"Extension '{extension.name}' has no extension_instance")
        return instance
    except ImportError as e:
        raise ValueError(f"Failed to import extension '{extension.name}' from '{extension.source}': {e}")


def send_payload(
    extension_instance: Any,
    tool_name: str, 
    arguments: Dict[str, Any],
    timeout: Optional[float] = None
) -> ExecutionResult:
    """
    Execute a tool and return standardized result.
    
    Args:
        extension_instance: The loaded extension instance
        tool_name: Name of the tool to call
        arguments: Arguments to pass to the tool
        timeout: Optional timeout in seconds
        
    Returns:
        Standardized ExecutionResult
    """
    try:
        # Call the tool
        raw_result = extension_instance.call_tool(tool_name, arguments)
        return parse_observation(raw_result)
    except Exception as e:
        return ExecutionResult(
            stderr=str(e),
            exit_code=1,
            is_error=True,
            result={"error": str(e)}
        )


def parse_observation(raw_output: Dict[str, Any]) -> ExecutionResult:
    """
    Convert raw extension output to standardized ExecutionResult.
    
    Handles the MCP-like format:
    {
        "content": [{"type": "text", "text": "..."}],
        "isError": bool
    }
    
    Args:
        raw_output: Raw output from extension call_tool
        
    Returns:
        Standardized ExecutionResult
    """
    is_error = raw_output.get("isError", False)
    
    # Extract text content
    content = raw_output.get("content", [])
    stdout_parts = []
    stderr_parts = []
    
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
            if is_error:
                stderr_parts.append(text)
            else:
                stdout_parts.append(text)
    
    return ExecutionResult(
        stdout="\n".join(stdout_parts),
        stderr="\n".join(stderr_parts),
        exit_code=1 if is_error else 0,
        is_error=is_error,
        result=raw_output
    )
