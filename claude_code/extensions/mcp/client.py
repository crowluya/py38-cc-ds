"""
MCP Client implementation for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides stdio-based MCP server connection.
"""

import json
import subprocess
import sys
from typing import Any, Dict, List, Optional

from claude_code.extensions.mcp.protocol import MCPProtocol, MCPResponse


class MCPError(Exception):
    """MCP-related error."""

    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(message)
        self.code = code


class MCPClient:
    """
    MCP Client for communicating with MCP servers.

    Supports stdio transport (subprocess communication).
    """

    def __init__(
        self,
        server_name: str,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP client.

        Args:
            server_name: Name of the MCP server
            config: Server configuration with command, args, env
        """
        self._server_name = server_name
        self._config = config or {}
        self._protocol = MCPProtocol()
        self._process: Optional[subprocess.Popen] = None
        self._connected = False
        self._tools: List[Dict[str, Any]] = []
        self._server_info: Optional[Dict[str, Any]] = None

    @property
    def server_name(self) -> str:
        """Get server name."""
        return self._server_name

    @property
    def config(self) -> Dict[str, Any]:
        """Get server configuration."""
        return self._config

    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._connected and self._process is not None

    def connect(self) -> None:
        """
        Connect to the MCP server.

        Raises:
            MCPError: If connection fails
        """
        if self._connected:
            return

        command = self._config.get("command")
        if not command:
            raise MCPError("No command specified in server config")

        args = self._config.get("args", [])
        env = self._config.get("env")

        # Build environment
        process_env = None
        if env:
            import os
            process_env = os.environ.copy()
            process_env.update(env)

        try:
            # Start subprocess
            self._process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=process_env,
            )

            # Send initialize request
            self._initialize()
            self._connected = True

        except FileNotFoundError:
            raise MCPError(f"Command not found: {command}")
        except Exception as e:
            self._cleanup()
            raise MCPError(f"Failed to connect: {str(e)}")

    def _initialize(self) -> None:
        """
        Send initialize request and handle response.

        Raises:
            MCPError: If initialization fails
        """
        request = self._protocol.create_initialize_request()
        response = self._send_request(request)

        if not response.success:
            raise MCPError(f"Initialize failed: {response.error}")

        self._server_info = response.data

        # Send initialized notification
        notification = self._protocol.create_notification("notifications/initialized")
        self._send_notification(notification)

    def _send_request(self, request: Dict[str, Any]) -> MCPResponse:
        """
        Send a request and wait for response.

        Args:
            request: Request dictionary

        Returns:
            MCPResponse with result or error
        """
        if not self._process or not self._process.stdin or not self._process.stdout:
            return MCPResponse(success=False, error="Not connected")

        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            self._process.stdin.write(request_str.encode("utf-8"))
            self._process.stdin.flush()

            # Read response
            response_line = self._process.stdout.readline()
            if not response_line:
                return MCPResponse(success=False, error="No response from server")

            return self._protocol.parse_response(response_line.decode("utf-8"))

        except Exception as e:
            return MCPResponse(success=False, error=str(e))

    def _send_notification(self, notification: Dict[str, Any]) -> None:
        """
        Send a notification (no response expected).

        Args:
            notification: Notification dictionary
        """
        if not self._process or not self._process.stdin:
            return

        try:
            notification_str = json.dumps(notification) + "\n"
            self._process.stdin.write(notification_str.encode("utf-8"))
            self._process.stdin.flush()
        except Exception:
            pass  # Notifications don't require response

    def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        self._cleanup()
        self._connected = False

    def _cleanup(self) -> None:
        """Clean up subprocess resources."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the server.

        Returns:
            List of tool definitions
        """
        if not self._connected:
            return []

        request = self._protocol.create_tools_list_request()
        response = self._send_request(request)

        if not response.success:
            return []

        tools = response.data.get("tools", []) if response.data else []
        self._tools = tools
        return tools

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Call a tool on the server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            MCPError: If not connected or call fails
        """
        if not self._connected:
            raise MCPError("Not connected to server")

        request = self._protocol.create_tools_call_request(name, arguments)
        response = self._send_request(request)

        if not response.success:
            raise MCPError(f"Tool call failed: {response.error}", response.error_code)

        return response.data or {}

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
