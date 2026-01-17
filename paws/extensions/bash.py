import subprocess
from typing import Dict, Any, List

class BashExtension:
    """
    A minimal MCP-like server for Bash commands.
    """
    def __init__(self):
        self.name = "Bash"

    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Returns the MCP tool definition.
        """
        return {
            "name": "execute_command",
            "description": "Execute a bash command on the host system.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute"
                    }
                },
                "required": ["command"]
            }
        }

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handlers the tool execution request.
        """
        if name != "execute_command":
            raise ValueError(f"Unknown tool: {name}")

        command = arguments.get("command")
        if not command:
            raise ValueError("Missing 'command' argument")

        try:
            # Running with shell=True to allow complex bash commands (pipes, etc)
            # Security warning: This is a PoC running on localhost as requested.
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": result.stdout if result.returncode == 0 else f"Error (Exit Code {result.returncode}):\n{result.stderr}\n{result.stdout}"
                    }
                ],
                "isError": result.returncode != 0
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(e)
                    }
                ],
                "isError": True
            }

# Singleton instance export
extension_instance = BashExtension()
