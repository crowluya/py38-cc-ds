"""
MCP Protocol implementation for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Implements JSON-RPC 2.0 based MCP protocol.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MCPResponse:
    """Response from MCP server."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[int] = None


class MCPProtocol:
    """
    MCP Protocol handler for JSON-RPC 2.0 communication.

    Handles:
    - Request creation with auto-incrementing IDs
    - Response parsing
    - Error handling
    """

    def __init__(self):
        """Initialize protocol handler."""
        self._request_id = 0

    def create_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a JSON-RPC 2.0 request.

        Args:
            method: RPC method name (e.g., "tools/list", "tools/call")
            params: Method parameters

        Returns:
            JSON-RPC request dictionary
        """
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        return request

    def create_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a JSON-RPC 2.0 notification (no response expected).

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            JSON-RPC notification dictionary (no id field)
        """
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }

    def parse_response(self, response_str: str) -> MCPResponse:
        """
        Parse a JSON-RPC 2.0 response.

        Args:
            response_str: Raw JSON response string

        Returns:
            MCPResponse with parsed data or error
        """
        try:
            data = json.loads(response_str)
        except json.JSONDecodeError as e:
            return MCPResponse(
                success=False,
                error=f"Invalid JSON response: {str(e)}",
            )

        # Check for error response
        if "error" in data:
            error_obj = data["error"]
            error_msg = error_obj.get("message", "Unknown error")
            error_code = error_obj.get("code")
            return MCPResponse(
                success=False,
                error=error_msg,
                error_code=error_code,
            )

        # Success response
        result = data.get("result")
        return MCPResponse(
            success=True,
            data=result,
        )

    def serialize_request(self, request: Dict[str, Any]) -> str:
        """
        Serialize a request to JSON string.

        Args:
            request: Request dictionary

        Returns:
            JSON string
        """
        return json.dumps(request)

    def create_initialize_request(
        self,
        client_info: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create an initialize request.

        Args:
            client_info: Client information (name, version)

        Returns:
            Initialize request dictionary
        """
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "clientInfo": client_info or {
                "name": "claude-code-python",
                "version": "1.0.0",
            },
        }
        return self.create_request("initialize", params)

    def create_tools_list_request(self) -> Dict[str, Any]:
        """
        Create a tools/list request.

        Returns:
            Tools list request dictionary
        """
        return self.create_request("tools/list", {})

    def create_tools_call_request(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a tools/call request.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tools call request dictionary
        """
        params = {
            "name": name,
            "arguments": arguments or {},
        }
        return self.create_request("tools/call", params)


def parse_tool_definition(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse an MCP tool definition into internal format.

    Args:
        mcp_tool: MCP tool definition from server

    Returns:
        Internal tool definition dictionary
    """
    name = mcp_tool.get("name", "")
    description = mcp_tool.get("description", "")
    input_schema = mcp_tool.get("inputSchema", {})

    # Convert inputSchema to parameters format
    parameters = {}
    if input_schema:
        parameters = {
            "type": input_schema.get("type", "object"),
            "properties": input_schema.get("properties", {}),
        }
        if "required" in input_schema:
            parameters["required"] = input_schema["required"]

    return {
        "name": name,
        "description": description,
        "parameters": parameters,
        "input_schema": input_schema,  # Keep original for reference
    }
