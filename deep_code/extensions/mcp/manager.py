"""
MCP Server Manager - Connection Pool and Lifecycle Management

Python 3.8.10 compatible
Implements MCP server management with connection pooling and health checks.
"""

import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from deep_code.extensions.mcp.client import MCPClient
from deep_code.extensions.mcp.config import (
    MCPConfig,
    MCPServerConfig,
    load_scoped_config,
)
from deep_code.extensions.mcp.transport_stdio import StdioTransport
from deep_code.extensions.mcp.transport_http import HttpTransport
from deep_code.extensions.mcp.transport_sse import SseTransport


class ServerStatus(Enum):
    """MCP server connection status."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ServerState:
    """State of a managed MCP server."""

    config: MCPServerConfig
    status: ServerStatus = ServerStatus.DISCONNECTED
    client: Optional[MCPClient] = None
    error_message: Optional[str] = None
    last_health_check: Optional[float] = None
    connect_attempts: int = 0


class MCPManager:
    """
    MCP Server Manager.

    Manages multiple MCP server connections with:
    - Connection pooling
    - Automatic reconnection
    - Health checks
    - Lifecycle management
    """

    DEFAULT_HEALTH_CHECK_INTERVAL = 30.0  # seconds
    MAX_CONNECT_ATTEMPTS = 3

    def __init__(
        self,
        project_root: Optional[Path] = None,
        auto_connect: bool = False,
        health_check_interval: float = DEFAULT_HEALTH_CHECK_INTERVAL,
    ) -> None:
        """
        Initialize MCP manager.

        Args:
            project_root: Project root directory
            auto_connect: Whether to auto-connect on load
            health_check_interval: Health check interval in seconds
        """
        self._project_root = project_root or Path.cwd()
        self._auto_connect = auto_connect
        self._health_check_interval = health_check_interval

        # Server states
        self._servers: Dict[str, ServerState] = {}
        self._lock = threading.Lock()

        # Health check thread
        self._health_check_thread: Optional[threading.Thread] = None
        self._health_check_running = False

        # Event callbacks
        self._on_connect_callbacks: List[Callable[[str], None]] = []
        self._on_disconnect_callbacks: List[Callable[[str, Optional[str]], None]] = []
        self._on_error_callbacks: List[Callable[[str, str], None]] = []

    def load_config(self, scopes: Optional[List[str]] = None) -> None:
        """
        Load server configurations from config files.

        Args:
            scopes: Scopes to load (defaults to all)
        """
        config = load_scoped_config(self._project_root, scopes)

        with self._lock:
            # Add new servers
            for name in config.list_servers():
                server_config = config.get_server(name)
                if server_config and name not in self._servers:
                    self._servers[name] = ServerState(config=server_config)

        if self._auto_connect:
            self.connect_all()

    def add_server(
        self,
        config: Union[MCPServerConfig, Dict[str, Any]],
        name: Optional[str] = None,
    ) -> None:
        """
        Add a server configuration.

        Args:
            config: Server configuration (MCPServerConfig or dict)
            name: Server name (required if config is dict)
        """
        if isinstance(config, dict):
            if not name:
                raise ValueError("name is required when config is a dict")
            server_config = MCPServerConfig.from_dict(name, config)
        else:
            server_config = config

        with self._lock:
            self._servers[server_config.name] = ServerState(config=server_config)

    def remove_server(self, name: str) -> bool:
        """
        Remove a server.

        Args:
            name: Server name

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if name in self._servers:
                state = self._servers[name]
                if state.client:
                    try:
                        state.client.close()
                    except Exception:
                        pass
                del self._servers[name]
                return True
        return False

    def connect(self, name: str) -> bool:
        """
        Connect to a server.

        Args:
            name: Server name

        Returns:
            True if connected successfully
        """
        with self._lock:
            if name not in self._servers:
                return False
            state = self._servers[name]

        if state.status == ServerStatus.CONNECTED:
            return True

        state.status = ServerStatus.CONNECTING
        state.connect_attempts += 1

        try:
            # Create transport based on config
            transport = self._create_transport(state.config)

            # Start transport if needed
            if isinstance(transport, StdioTransport):
                transport.start()
            elif isinstance(transport, SseTransport):
                transport.start()

            # Create and initialize client
            client = MCPClient(transport)
            client.initialize()

            state.client = client
            state.status = ServerStatus.CONNECTED
            state.error_message = None
            state.connect_attempts = 0
            state.last_health_check = time.time()

            # Notify callbacks
            for callback in self._on_connect_callbacks:
                try:
                    callback(name)
                except Exception:
                    pass

            return True

        except Exception as e:
            state.status = ServerStatus.ERROR
            state.error_message = str(e)
            state.client = None

            # Notify callbacks
            for callback in self._on_error_callbacks:
                try:
                    callback(name, str(e))
                except Exception:
                    pass

            return False

    def disconnect(self, name: str) -> bool:
        """
        Disconnect from a server.

        Args:
            name: Server name

        Returns:
            True if disconnected successfully
        """
        with self._lock:
            if name not in self._servers:
                return False
            state = self._servers[name]

        if state.status == ServerStatus.DISCONNECTED:
            return True

        error_msg = None
        try:
            if state.client:
                state.client.close()
        except Exception as e:
            error_msg = str(e)

        state.client = None
        state.status = ServerStatus.DISCONNECTED

        # Notify callbacks
        for callback in self._on_disconnect_callbacks:
            try:
                callback(name, error_msg)
            except Exception:
                pass

        return True

    def connect_all(self) -> Dict[str, bool]:
        """
        Connect to all configured servers.

        Returns:
            Dictionary mapping server name to connection success
        """
        results: Dict[str, bool] = {}
        with self._lock:
            names = list(self._servers.keys())

        for name in names:
            results[name] = self.connect(name)

        return results

    def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        with self._lock:
            names = list(self._servers.keys())

        for name in names:
            self.disconnect(name)

    def get_client(self, name: str) -> Optional[MCPClient]:
        """
        Get client for a server.

        Args:
            name: Server name

        Returns:
            MCPClient or None if not connected
        """
        with self._lock:
            if name in self._servers:
                state = self._servers[name]
                if state.status == ServerStatus.CONNECTED:
                    return state.client
        return None

    def get_status(self, name: str) -> Optional[ServerStatus]:
        """
        Get server status.

        Args:
            name: Server name

        Returns:
            ServerStatus or None if not found
        """
        with self._lock:
            if name in self._servers:
                return self._servers[name].status
        return None

    def get_all_status(self) -> Dict[str, ServerStatus]:
        """
        Get status of all servers.

        Returns:
            Dictionary mapping server name to status
        """
        with self._lock:
            return {
                name: state.status
                for name, state in self._servers.items()
            }

    def list_servers(self) -> List[str]:
        """List all server names."""
        with self._lock:
            return list(self._servers.keys())

    def list_connected_servers(self) -> List[str]:
        """List connected server names."""
        with self._lock:
            return [
                name for name, state in self._servers.items()
                if state.status == ServerStatus.CONNECTED
            ]

    def get_server_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed server information.

        Args:
            name: Server name

        Returns:
            Server info dictionary or None
        """
        with self._lock:
            if name not in self._servers:
                return None
            state = self._servers[name]

        return {
            "name": name,
            "status": state.status.value,
            "transport_type": state.config.transport_type,
            "error_message": state.error_message,
            "connect_attempts": state.connect_attempts,
            "last_health_check": state.last_health_check,
            "server_info": state.client.server_info if state.client else None,
            "capabilities": state.client.capabilities if state.client else None,
        }

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Get all tools from all connected servers.

        Returns:
            List of tool definitions with server info
        """
        all_tools: List[Dict[str, Any]] = []
        with self._lock:
            connected = [
                (name, state.client)
                for name, state in self._servers.items()
                if state.status == ServerStatus.CONNECTED and state.client
            ]

        for name, client in connected:
            try:
                tools = client.list_tools()
                for tool in tools:
                    tool_with_server = dict(tool)
                    tool_with_server["_server"] = name
                    all_tools.append(tool_with_server)
            except Exception:
                pass

        return all_tools

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Call a tool on a specific server.

        Args:
            server_name: Server name
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            RuntimeError: If server not found or call fails
        """
        client = self.get_client(server_name)
        if not client:
            raise RuntimeError(f"Server not connected: {server_name}")

        return client.call_tool(tool_name, arguments)

    # Health check methods

    def start_health_checks(self) -> None:
        """Start background health check thread."""
        if self._health_check_running:
            return

        self._health_check_running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
        )
        self._health_check_thread.start()

    def stop_health_checks(self) -> None:
        """Stop background health check thread."""
        self._health_check_running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=2.0)
            self._health_check_thread = None

    def check_health(self, name: str) -> bool:
        """
        Check health of a server.

        Args:
            name: Server name

        Returns:
            True if healthy
        """
        with self._lock:
            if name not in self._servers:
                return False
            state = self._servers[name]

        if state.status != ServerStatus.CONNECTED or not state.client:
            return False

        try:
            # Try to list tools as a health check
            state.client.list_tools()
            state.last_health_check = time.time()
            return True
        except Exception as e:
            state.status = ServerStatus.ERROR
            state.error_message = f"Health check failed: {e}"
            return False

    def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self._health_check_running:
            with self._lock:
                names = [
                    name for name, state in self._servers.items()
                    if state.status == ServerStatus.CONNECTED
                ]

            for name in names:
                if not self._health_check_running:
                    break

                healthy = self.check_health(name)
                if not healthy:
                    # Try to reconnect
                    with self._lock:
                        state = self._servers.get(name)
                        if state and state.connect_attempts < self.MAX_CONNECT_ATTEMPTS:
                            self.disconnect(name)
                            self.connect(name)

            # Sleep in small intervals to allow quick shutdown
            for _ in range(int(self._health_check_interval)):
                if not self._health_check_running:
                    break
                time.sleep(1.0)

    # Event callbacks

    def on_connect(self, callback: Callable[[str], None]) -> None:
        """Register connect callback."""
        self._on_connect_callbacks.append(callback)

    def on_disconnect(self, callback: Callable[[str, Optional[str]], None]) -> None:
        """Register disconnect callback."""
        self._on_disconnect_callbacks.append(callback)

    def on_error(self, callback: Callable[[str, str], None]) -> None:
        """Register error callback."""
        self._on_error_callbacks.append(callback)

    # Transport creation

    def _create_transport(self, config: MCPServerConfig):
        """
        Create transport from server config.

        Args:
            config: Server configuration

        Returns:
            Transport instance
        """
        if config.transport_type == "stdio":
            if not config.command:
                raise ValueError(f"Server {config.name}: stdio transport requires command")
            return StdioTransport(
                command=config.command,
                args=config.args,
                env=config.env,
            )
        elif config.transport_type == "http":
            if not config.url:
                raise ValueError(f"Server {config.name}: http transport requires url")
            return HttpTransport(
                url=config.url,
                headers=config.headers,
            )
        elif config.transport_type == "sse":
            if not config.url:
                raise ValueError(f"Server {config.name}: sse transport requires url")
            return SseTransport(
                url=config.url,
                headers=config.headers,
            )
        else:
            raise ValueError(f"Unknown transport type: {config.transport_type}")

    # Context manager and cleanup

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_health_checks()
        self.disconnect_all()

    def close(self) -> None:
        """Close manager and all connections."""
        self.stop_health_checks()
        self.disconnect_all()

    def __len__(self) -> int:
        """Return number of configured servers."""
        return len(self._servers)

    def __contains__(self, name: str) -> bool:
        """Check if server is configured."""
        return name in self._servers
