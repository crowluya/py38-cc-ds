"""
MCP Tool Wrapper for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Wraps MCP tools to integrate with ToolRegistry.
"""

from typing import Any, Dict, List, Optional

from claude_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from claude_code.extensions.mcp.client import MCPClient, MCPError


class MCPToolWrapper(Tool):
    """
    Wrapper that adapts MCP tools to the Tool interface.

    Allows MCP tools to be registered in ToolRegistry and
    called like native tools.
    """

    def __init__(
        self,
        tool_definition: Dict[str, Any],
        mcp_client: MCPClient,
        server_name: str,
    ):
        """
        Initialize MCP tool wrapper.

        Args:
            tool_definition: MCP tool definition from server
            mcp_client: MCP client for calling the tool
            server_name: Name of the MCP server
        """
        self._tool_definition = tool_definition
        self._mcp_client = mcp_client
        self._server_name = server_name
        self._tool_name = tool_definition.get("name", "")
        self._description = tool_definition.get("description", "")
        self._input_schema = tool_definition.get("inputSchema", {})

    @property
    def name(self) -> str:
        """
        Get tool name with MCP prefix.

        Format: mcp__<server_name>__<tool_name>
        """
        return f"mcp__{self._server_name}__{self._tool_name}"

    @property
    def original_name(self) -> str:
        """Get original tool name without prefix."""
        return self._tool_name

    @property
    def description(self) -> str:
        """Get tool description."""
        return self._description

    @property
    def category(self) -> ToolCategory:
        """Get tool category."""
        return ToolCategory.MCP

    @property
    def parameters(self) -> List[ToolParameter]:
        """
        Get tool parameters from input schema.

        Returns:
            List of ToolParameter objects
        """
        params = []
        properties = self._input_schema.get("properties", {})
        required = self._input_schema.get("required", [])

        for prop_name, prop_def in properties.items():
            param = ToolParameter(
                name=prop_name,
                type=prop_def.get("type", "string"),
                description=prop_def.get("description", ""),
                required=prop_name in required,
                default=prop_def.get("default"),
                enum=prop_def.get("enum"),
            )
            params.append(param)

        return params

    @property
    def requires_permission(self) -> bool:
        """MCP tools require permission by default."""
        return True

    @property
    def is_dangerous(self) -> bool:
        """MCP tools are not marked as dangerous by default."""
        return False

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the MCP tool.

        Args:
            arguments: Tool arguments

        Returns:
            ToolResult with execution result
        """
        try:
            result = self._mcp_client.call_tool(self._tool_name, arguments)

            # Format result as string
            if isinstance(result, dict):
                # Check for content array (MCP standard format)
                content = result.get("content", [])
                if content and isinstance(content, list):
                    output_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                output_parts.append(item.get("text", ""))
                            elif item.get("type") == "image":
                                output_parts.append("[Image content]")
                            else:
                                output_parts.append(str(item))
                        else:
                            output_parts.append(str(item))
                    output = "\n".join(output_parts)
                else:
                    import json
                    output = json.dumps(result, indent=2)
            else:
                output = str(result)

            return ToolResult.success_result(
                self.name,
                output,
                metadata={
                    "server": self._server_name,
                    "original_tool": self._tool_name,
                },
            )

        except MCPError as e:
            return ToolResult.error_result(
                self.name,
                f"MCP tool execution failed: {str(e)}",
                metadata={
                    "server": self._server_name,
                    "original_tool": self._tool_name,
                    "error_code": e.code,
                },
            )
        except Exception as e:
            return ToolResult.error_result(
                self.name,
                f"Unexpected error: {str(e)}",
                metadata={
                    "server": self._server_name,
                    "original_tool": self._tool_name,
                },
            )

    def get_json_schema(self) -> Dict[str, Any]:
        """
        Get OpenAI-compatible function schema.

        Returns:
            JSON Schema for the tool
        """
        # Build parameters from input schema
        parameters = {
            "type": "object",
            "properties": self._input_schema.get("properties", {}),
        }

        required = self._input_schema.get("required", [])
        if required:
            parameters["required"] = required

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self._description,
                "parameters": parameters,
            },
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"<MCPToolWrapper name={self.name} server={self._server_name}>"
