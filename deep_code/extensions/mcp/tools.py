"""
MCP Tool Wrapper for DeepCode

Python 3.8.10 compatible
Wraps MCP tools to integrate with ToolRegistry.
Implements MCP-013 (tool wrapper) and MCP-014 (tool call routing).
"""

import json
from typing import Any, Dict, List, Optional

from deep_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
    ToolValidationError,
)
from deep_code.extensions.mcp.client import MCPClient


# Output limits (MCP-014)
DEFAULT_OUTPUT_LIMIT = 10000  # 10k characters
MAX_OUTPUT_LIMIT = 25000  # 25k characters


def truncate_output(output: str, limit: int = DEFAULT_OUTPUT_LIMIT) -> str:
    """
    Truncate output to specified limit.

    Args:
        output: Output string
        limit: Character limit

    Returns:
        Truncated output with indicator if truncated
    """
    if len(output) <= limit:
        return output

    truncated = output[:limit]
    remaining = len(output) - limit
    return f"{truncated}\n\n[Output truncated. {remaining} more characters not shown.]"


def validate_json_schema(value: Any, schema: Dict[str, Any], path: str = "") -> List[str]:
    """
    Validate a value against JSON Schema.

    Args:
        value: Value to validate
        schema: JSON Schema
        path: Current path for error messages

    Returns:
        List of validation errors (empty if valid)
    """
    errors: List[str] = []
    schema_type = schema.get("type")

    if schema_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return errors

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Check required properties
        for req in required:
            if req not in value:
                errors.append(f"{path}.{req}: required property missing")

        # Validate each property
        for prop_name, prop_value in value.items():
            if prop_name in properties:
                prop_schema = properties[prop_name]
                prop_path = f"{path}.{prop_name}" if path else prop_name
                errors.extend(validate_json_schema(prop_value, prop_schema, prop_path))

    elif schema_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
            return errors

        items_schema = schema.get("items", {})
        for i, item in enumerate(value):
            item_path = f"{path}[{i}]"
            errors.extend(validate_json_schema(item, items_schema, item_path))

    elif schema_type == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")

        # Check enum
        enum_values = schema.get("enum")
        if enum_values and value not in enum_values:
            errors.append(f"{path}: value must be one of {enum_values}")

    elif schema_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer, got {type(value).__name__}")

    elif schema_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{path}: expected number, got {type(value).__name__}")

    elif schema_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{path}: expected boolean, got {type(value).__name__}")

    elif schema_type == "null":
        if value is not None:
            errors.append(f"{path}: expected null, got {type(value).__name__}")

    return errors


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
        output_limit: int = DEFAULT_OUTPUT_LIMIT,
    ):
        """
        Initialize MCP tool wrapper.

        Args:
            tool_definition: MCP tool definition from server
            mcp_client: MCP client for calling the tool
            server_name: Name of the MCP server
            output_limit: Maximum output characters
        """
        self._tool_definition = tool_definition
        self._mcp_client = mcp_client
        self._server_name = server_name
        self._tool_name = tool_definition.get("name", "")
        self._description = tool_definition.get("description", "")
        self._input_schema = tool_definition.get("inputSchema", {})
        self._output_limit = min(output_limit, MAX_OUTPUT_LIMIT)

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
    def server_name(self) -> str:
        """Get server name."""
        return self._server_name

    @property
    def description(self) -> str:
        """Get tool description."""
        return self._description

    @property
    def category(self) -> ToolCategory:
        """Get tool category."""
        return ToolCategory.MCP

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get input JSON Schema."""
        return self._input_schema

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

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """
        Validate tool arguments against JSON Schema.

        Args:
            arguments: Arguments to validate

        Raises:
            ToolValidationError: If validation fails
        """
        if not self._input_schema:
            return

        errors = validate_json_schema(arguments, self._input_schema)
        if errors:
            raise ToolValidationError(
                f"Invalid arguments: {'; '.join(errors)}",
                tool_name=self.name,
            )

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the MCP tool.

        Args:
            arguments: Tool arguments

        Returns:
            ToolResult with execution result
        """
        # Validate arguments
        try:
            self.validate_arguments(arguments)
        except ToolValidationError as e:
            return ToolResult.error_result(
                self.name,
                str(e),
                metadata={
                    "server": self._server_name,
                    "original_tool": self._tool_name,
                },
            )

        try:
            result = self._mcp_client.call_tool(self._tool_name, arguments)

            # Format result as string
            output = self._format_result(result)

            # Truncate if needed (MCP-014)
            output = truncate_output(output, self._output_limit)

            return ToolResult.success_result(
                self.name,
                output,
                metadata={
                    "server": self._server_name,
                    "original_tool": self._tool_name,
                },
            )

        except RuntimeError as e:
            return ToolResult.error_result(
                self.name,
                f"MCP tool execution failed: {str(e)}",
                metadata={
                    "server": self._server_name,
                    "original_tool": self._tool_name,
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

    def _format_result(self, result: Any) -> str:
        """
        Format MCP tool result as string.

        Args:
            result: Raw result from MCP tool

        Returns:
            Formatted string output
        """
        if result is None:
            return ""

        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            # Check for content array (MCP standard format)
            content = result.get("content", [])
            if content and isinstance(content, list):
                output_parts = []
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type", "")
                        if item_type == "text":
                            output_parts.append(item.get("text", ""))
                        elif item_type == "image":
                            # Include image info
                            mime_type = item.get("mimeType", "image/*")
                            output_parts.append(f"[Image: {mime_type}]")
                        elif item_type == "resource":
                            uri = item.get("resource", {}).get("uri", "")
                            output_parts.append(f"[Resource: {uri}]")
                        else:
                            output_parts.append(json.dumps(item, indent=2))
                    else:
                        output_parts.append(str(item))
                return "\n".join(output_parts)
            else:
                return json.dumps(result, indent=2, ensure_ascii=False)

        if isinstance(result, list):
            return json.dumps(result, indent=2, ensure_ascii=False)

        return str(result)

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


# MCP-014: Tool call routing

class MCPToolRouter:
    """
    Routes tool calls to appropriate MCP servers.

    Manages tool name resolution and dispatching.
    """

    def __init__(self) -> None:
        """Initialize tool router."""
        self._tools: Dict[str, MCPToolWrapper] = {}
        self._by_server: Dict[str, Dict[str, MCPToolWrapper]] = {}

    def register(self, tool: MCPToolWrapper) -> None:
        """
        Register a tool.

        Args:
            tool: Tool to register
        """
        self._tools[tool.name] = tool

        # Index by server
        if tool.server_name not in self._by_server:
            self._by_server[tool.server_name] = {}
        self._by_server[tool.server_name][tool.original_name] = tool

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name

        Returns:
            True if unregistered
        """
        if name in self._tools:
            tool = self._tools[name]
            del self._tools[name]

            # Remove from server index
            if tool.server_name in self._by_server:
                if tool.original_name in self._by_server[tool.server_name]:
                    del self._by_server[tool.server_name][tool.original_name]

            return True
        return False

    def get(self, name: str) -> Optional[MCPToolWrapper]:
        """
        Get tool by name.

        Args:
            name: Tool name (full or original)

        Returns:
            Tool or None
        """
        # Try full name first
        if name in self._tools:
            return self._tools[name]

        # Try to find by original name (ambiguous if multiple servers)
        for server_tools in self._by_server.values():
            if name in server_tools:
                return server_tools[name]

        return None

    def get_by_server(
        self,
        server_name: str,
        tool_name: str,
    ) -> Optional[MCPToolWrapper]:
        """
        Get tool by server and original name.

        Args:
            server_name: Server name
            tool_name: Original tool name

        Returns:
            Tool or None
        """
        if server_name in self._by_server:
            return self._by_server[server_name].get(tool_name)
        return None

    def call(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """
        Call a tool by name.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            ToolResult
        """
        tool = self.get(name)
        if not tool:
            return ToolResult.error_result(
                name,
                f"Tool not found: {name}",
            )

        return tool.execute(arguments or {})

    def list_tools(self) -> List[MCPToolWrapper]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_by_server(self, server_name: str) -> List[MCPToolWrapper]:
        """List tools for a specific server."""
        if server_name in self._by_server:
            return list(self._by_server[server_name].values())
        return []

    def list_servers(self) -> List[str]:
        """List all servers with registered tools."""
        return list(self._by_server.keys())

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._by_server.clear()

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools or self.get(name) is not None
