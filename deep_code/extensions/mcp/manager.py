"""
MCP Manager for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Manages multiple MCP server connections and tool registration.
"""

from typing import Any, Dict, List, Optional

from deep_code.core.tools.registry import ToolRegistry
from deep_code.extensions.mcp.client import MCPClient, MCPError
from deep_code.extensions.mcp.config import MCPConfig
from deep_code.extensions.mcp.tools import MCPToolWrapper


class MCPManager:
    """
    Manager for multiple MCP server connections.

    Handles:
    - Adding/removing servers
    - Connecting/disconnecting all servers
    - Collecting tools from all servers
    - Registering tools to ToolRegistry
    """

    def __init__(self, config: Optional[MCPConfig] = None):
        """
        Initialize MCP manager.

        Args:
            config: Optional MCP configuration to load servers from
        """
        self._clients: Dict[str, MCPClient] = {}
        self._config = config

        # Load servers from config if provided
        if config:
            for name in config.list_servers():
                server_config = config.get_server(name)
                if server_config:
                    self.add_server(name, server_config)

    @property
    def clients(self) -> Dict[str, MCPClient]:
        """Get all MCP clients."""
        return self._clients

    def add_server(self, name: str, config: Dict[str, Any]) -> MCPClient:
        """
        Add an MCP server.

        Args:
            name: Server name
            config: Server configuration

        Returns:
            MCPClient instance
        """
        client = MCPClient(server_name=name, config=config)
        self._clients[name] = client
        return client

    def remove_server(self, name: str) -> bool:
        """
        Remove an MCP server.

        Args:
            name: Server name

        Returns:
            True if removed, False if not found
        """
        if name in self._clients:
            client = self._clients[name]
            if client.is_connected:
                client.disconnect()
            del self._clients[name]
            return True
        return False

    def get_client(self, name: str) -> Optional[MCPClient]:
        """
        Get an MCP client by name.

        Args:
            name: Server name

        Returns:
            MCPClient or None if not found
        """
        return self._clients.get(name)

    def connect_all(self) -> Dict[str, Optional[str]]:
        """
        Connect to all configured servers.

        Returns:
            Dictionary of server names to error messages (None if success)
        """
        results = {}
        for name, client in self._clients.items():
            try:
                client.connect()
                results[name] = None
            except MCPError as e:
                results[name] = str(e)
            except Exception as e:
                results[name] = f"Unexpected error: {str(e)}"
        return results

    def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for client in self._clients.values():
            if client.is_connected:
                client.disconnect()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Get all tools from all connected servers.

        Returns:
            List of tool definitions with server info
        """
        all_tools = []
        for name, client in self._clients.items():
            if client.is_connected:
                try:
                    tools = client.list_tools()
                    for tool in tools:
                        tool_with_server = dict(tool)
                        tool_with_server["_server"] = name
                        all_tools.append(tool_with_server)
                except Exception:
                    pass  # Skip servers that fail to list tools
        return all_tools

    def register_tools(
        self,
        registry: ToolRegistry,
        replace: bool = False,
    ) -> int:
        """
        Register all MCP tools to a ToolRegistry.

        Args:
            registry: ToolRegistry to register tools to
            replace: Replace existing tools with same name

        Returns:
            Number of tools registered
        """
        count = 0
        for name, client in self._clients.items():
            if client.is_connected:
                try:
                    tools = client.list_tools()
                    for tool_def in tools:
                        wrapper = MCPToolWrapper(
                            tool_definition=tool_def,
                            mcp_client=client,
                            server_name=name,
                        )
                        try:
                            registry.register(wrapper, replace=replace)
                            count += 1
                        except Exception:
                            pass  # Skip tools that fail to register
                except Exception:
                    pass  # Skip servers that fail
        return count

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Call a tool on a specific server.

        Args:
            server_name: Server name
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            MCPError: If server not found or call fails
        """
        client = self._clients.get(server_name)
        if not client:
            raise MCPError(f"Server not found: {server_name}")

        if not client.is_connected:
            raise MCPError(f"Server not connected: {server_name}")

        return client.call_tool(tool_name, arguments)

    def list_servers(self) -> List[str]:
        """
        List all configured server names.

        Returns:
            List of server names
        """
        return list(self._clients.keys())

    def get_connected_servers(self) -> List[str]:
        """
        List all connected server names.

        Returns:
            List of connected server names
        """
        return [
            name for name, client in self._clients.items()
            if client.is_connected
        ]

    def __len__(self) -> int:
        """Return number of configured servers."""
        return len(self._clients)

    def __contains__(self, name: str) -> bool:
        """Check if server is configured."""
        return name in self._clients

    def __enter__(self):
        """Context manager entry - connect all servers."""
        self.connect_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect all servers."""
        self.disconnect_all()
        return False
