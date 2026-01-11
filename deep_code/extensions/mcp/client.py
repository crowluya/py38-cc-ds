"""
MCP Client Core - Session Management

Python 3.8.10 compatible
Implements MCP client with initialize/shutdown handshake and request/response matching.
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union

from deep_code.extensions.mcp.protocol import (
    MCPRequest,
    MCPResponse,
    MCPNotification,
    create_request,
    create_error_response,
    ErrorCode,
)
from deep_code.extensions.mcp.transport_stdio import StdioTransport
from deep_code.extensions.mcp.transport_http import HttpTransport
from deep_code.extensions.mcp.transport_sse import SseTransport
from deep_code.extensions.mcp.capabilities import CapabilityCache


class MCPClient:
    """
    MCP client with session management.
    
    Handles initialize/shutdown handshake, request/response matching, and timeouts.
    """

    def __init__(
        self,
        transport: Union[StdioTransport, HttpTransport, SseTransport],
        default_timeout: float = 30.0,
    ) -> None:
        """
        Initialize MCP client.

        Args:
            transport: Transport layer (stdio/http/sse)
            default_timeout: Default request timeout in seconds
        """
        self._transport = transport
        self._default_timeout = default_timeout

        # Request/response matching
        self._pending_requests: Dict[Union[str, int], MCPResponse] = {}
        self._request_lock = threading.Lock()

        # Session state
        self._initialized = False
        self._server_info: Optional[Dict[str, Any]] = None
        self._capabilities: Optional[Dict[str, Any]] = None

        # Capability cache (MCP-009)
        self._capability_cache = CapabilityCache()

        # Notification handlers (MCP-009)
        self._notification_handlers: Dict[str, List[Callable[[MCPNotification], None]]] = {}

        # Background notification listener
        self._listener_thread: Optional[threading.Thread] = None
        self._listener_running = False

    def initialize(
        self,
        client_info: Optional[Dict[str, Any]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Initialize MCP session.

        Args:
            client_info: Client information (name, version)
            capabilities: Client capabilities

        Returns:
            Server information and capabilities

        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            raise RuntimeError("Client already initialized")

        # Default client info
        if client_info is None:
            client_info = {
                "name": "DeepCode",
                "version": "0.1.0",
            }

        # Default capabilities
        if capabilities is None:
            capabilities = {}

        # Send initialize request
        request = create_request(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "clientInfo": client_info,
                "capabilities": capabilities,
            },
        )

        response = self._send_request(request)

        if response.is_error:
            raise RuntimeError(f"Initialize failed: {response.error}")

        # Store server info
        result = response.result or {}
        self._server_info = result.get("serverInfo", {})
        self._capabilities = result.get("capabilities", {})
        self._initialized = True

        # Send initialized notification
        self._send_notification("notifications/initialized")

        # Register default notification handlers (MCP-009)
        self._register_default_handlers()

        # Start notification listener for stdio transport
        if isinstance(self._transport, StdioTransport):
            self._start_notification_listener()

        # Initial capability discovery
        self._refresh_capabilities()

        return result

    def shutdown(self) -> None:
        """Shutdown MCP session."""
        if not self._initialized:
            return

        # Stop notification listener
        self._stop_notification_listener()

        try:
            # Send shutdown request
            request = create_request(method="shutdown")
            self._send_request(request, timeout=5.0)
        except Exception:
            # Ignore errors during shutdown
            pass
        finally:
            self._initialized = False
            self._capability_cache.clear()

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            RuntimeError: If not initialized or call fails
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        request = create_request(
            method="tools/call",
            params={
                "name": name,
                "arguments": arguments or {},
            },
        )

        response = self._send_request(request)

        if response.is_error:
            raise RuntimeError(f"Tool call failed: {response.error}")

        return response.result

    def list_tools(self) -> list:
        """
        List available tools.

        Returns:
            List of tool definitions

        Raises:
            RuntimeError: If not initialized or request fails
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        request = create_request(method="tools/list")
        response = self._send_request(request)

        if response.is_error:
            raise RuntimeError(f"List tools failed: {response.error}")

        result = response.result or {}
        return result.get("tools", [])

    def list_resources(self) -> list:
        """
        List available resources.

        Returns:
            List of resource definitions

        Raises:
            RuntimeError: If not initialized or request fails
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        request = create_request(method="resources/list")
        response = self._send_request(request)

        if response.is_error:
            raise RuntimeError(f"List resources failed: {response.error}")

        result = response.result or {}
        return result.get("resources", [])

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a resource.

        Args:
            uri: Resource URI

        Returns:
            Resource content

        Raises:
            RuntimeError: If not initialized or request fails
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        request = create_request(
            method="resources/read",
            params={"uri": uri},
        )
        response = self._send_request(request)

        if response.is_error:
            raise RuntimeError(f"Read resource failed: {response.error}")

        return response.result or {}

    def list_prompts(self) -> list:
        """
        List available prompts.

        Returns:
            List of prompt definitions

        Raises:
            RuntimeError: If not initialized or request fails
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        request = create_request(method="prompts/list")
        response = self._send_request(request)

        if response.is_error:
            raise RuntimeError(f"List prompts failed: {response.error}")

        result = response.result or {}
        return result.get("prompts", [])

    def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get a prompt.

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt content

        Raises:
            RuntimeError: If not initialized or request fails
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        request = create_request(
            method="prompts/get",
            params={
                "name": name,
                "arguments": arguments or {},
            },
        )
        response = self._send_request(request)

        if response.is_error:
            raise RuntimeError(f"Get prompt failed: {response.error}")

        return response.result or {}

    def _send_request(
        self,
        request: MCPRequest,
        timeout: Optional[float] = None,
    ) -> MCPResponse:
        """
        Send a request and wait for response.

        Args:
            request: Request to send
            timeout: Timeout in seconds

        Returns:
            Response

        Raises:
            RuntimeError: If request fails or times out
        """
        timeout_val = timeout if timeout is not None else self._default_timeout

        # For HTTP transport, send directly
        if isinstance(self._transport, HttpTransport):
            return self._transport.send(request)

        # For stdio/sse transports, use async pattern
        request_id = request.id

        # Register pending request
        with self._request_lock:
            self._pending_requests[request_id] = None  # type: ignore

        try:
            # Send request
            if isinstance(self._transport, StdioTransport):
                self._transport.send(request)
            else:
                # SSE doesn't support sending requests
                raise RuntimeError("SSE transport doesn't support requests")

            # Wait for response
            start_time = time.time()
            while time.time() - start_time < timeout_val:
                with self._request_lock:
                    response = self._pending_requests.get(request_id)
                    if response is not None:
                        del self._pending_requests[request_id]
                        return response

                # Check for messages
                if isinstance(self._transport, StdioTransport):
                    msg = self._transport.receive(timeout=0.1)
                    if msg and isinstance(msg, MCPResponse):
                        with self._request_lock:
                            if msg.id in self._pending_requests:
                                self._pending_requests[msg.id] = msg

                time.sleep(0.01)

            # Timeout
            with self._request_lock:
                if request_id in self._pending_requests:
                    del self._pending_requests[request_id]

            return create_error_response(
                request_id=request_id,
                code=ErrorCode.TIMEOUT_ERROR,
                message=f"Request timeout after {timeout_val}s",
            )

        except Exception as e:
            with self._request_lock:
                if request_id in self._pending_requests:
                    del self._pending_requests[request_id]

            return create_error_response(
                request_id=request_id,
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Request failed: {e}",
            )

    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a notification (no response expected)."""
        from deep_code.extensions.mcp.protocol import create_notification

        notification = create_notification(method=method, params=params)

        if isinstance(self._transport, HttpTransport):
            # HTTP doesn't support notifications
            pass
        elif isinstance(self._transport, StdioTransport):
            self._transport.send(notification)

    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._initialized

    @property
    def server_info(self) -> Optional[Dict[str, Any]]:
        """Get server information."""
        return self._server_info

    @property
    def capabilities(self) -> Optional[Dict[str, Any]]:
        """Get server capabilities."""
        return self._capabilities

    @property
    def capability_cache(self) -> CapabilityCache:
        """Get capability cache."""
        return self._capability_cache

    # MCP-009: Dynamic Update Support

    def register_notification_handler(
        self,
        method: str,
        handler: Callable[[MCPNotification], None],
    ) -> None:
        """
        Register a handler for a notification method.

        Args:
            method: Notification method name
            handler: Handler function
        """
        if method not in self._notification_handlers:
            self._notification_handlers[method] = []
        self._notification_handlers[method].append(handler)

    def unregister_notification_handler(
        self,
        method: str,
        handler: Callable[[MCPNotification], None],
    ) -> None:
        """
        Unregister a notification handler.

        Args:
            method: Notification method name
            handler: Handler function to remove
        """
        if method in self._notification_handlers:
            try:
                self._notification_handlers[method].remove(handler)
            except ValueError:
                pass

    def _register_default_handlers(self) -> None:
        """Register default notification handlers for capability changes."""
        self.register_notification_handler(
            "notifications/tools/list_changed",
            self._on_tools_changed,
        )
        self.register_notification_handler(
            "notifications/resources/list_changed",
            self._on_resources_changed,
        )
        self.register_notification_handler(
            "notifications/prompts/list_changed",
            self._on_prompts_changed,
        )

    def _on_tools_changed(self, notification: MCPNotification) -> None:
        """Handle tools list changed notification."""
        try:
            tools = self.list_tools()
            self._capability_cache.update_tools(tools)
        except Exception:
            pass

    def _on_resources_changed(self, notification: MCPNotification) -> None:
        """Handle resources list changed notification."""
        try:
            resources = self.list_resources()
            self._capability_cache.update_resources(resources)
        except Exception:
            pass

    def _on_prompts_changed(self, notification: MCPNotification) -> None:
        """Handle prompts list changed notification."""
        try:
            prompts = self.list_prompts()
            self._capability_cache.update_prompts(prompts)
        except Exception:
            pass

    def _refresh_capabilities(self) -> None:
        """Refresh all capabilities from server."""
        try:
            tools = self.list_tools()
            self._capability_cache.update_tools(tools)
        except Exception:
            pass

        try:
            resources = self.list_resources()
            self._capability_cache.update_resources(resources)
        except Exception:
            pass

        try:
            prompts = self.list_prompts()
            self._capability_cache.update_prompts(prompts)
        except Exception:
            pass

    def _start_notification_listener(self) -> None:
        """Start background notification listener thread."""
        if self._listener_running:
            return

        self._listener_running = True
        self._listener_thread = threading.Thread(
            target=self._notification_listener_loop,
            daemon=True,
        )
        self._listener_thread.start()

    def _stop_notification_listener(self) -> None:
        """Stop background notification listener thread."""
        self._listener_running = False
        if self._listener_thread:
            self._listener_thread.join(timeout=1.0)
            self._listener_thread = None

    def _notification_listener_loop(self) -> None:
        """Background loop to listen for notifications."""
        while self._listener_running:
            try:
                if isinstance(self._transport, StdioTransport):
                    msg = self._transport.receive(timeout=0.1)
                    if msg:
                        self._handle_incoming_message(msg)
                elif isinstance(self._transport, SseTransport):
                    msg = self._transport.receive(timeout=0.1)
                    if msg:
                        self._handle_incoming_message(msg)
            except Exception:
                pass
            time.sleep(0.01)

    def _handle_incoming_message(
        self,
        message: Union[MCPRequest, MCPResponse, MCPNotification],
    ) -> None:
        """
        Handle an incoming message.

        Args:
            message: Incoming message
        """
        if isinstance(message, MCPResponse):
            # Match to pending request
            with self._request_lock:
                if message.id in self._pending_requests:
                    self._pending_requests[message.id] = message
        elif isinstance(message, MCPNotification):
            # Dispatch to handlers
            self._dispatch_notification(message)

    def _dispatch_notification(self, notification: MCPNotification) -> None:
        """
        Dispatch notification to registered handlers.

        Args:
            notification: Notification to dispatch
        """
        handlers = self._notification_handlers.get(notification.method, [])
        for handler in handlers:
            try:
                handler(notification)
            except Exception:
                pass

    def close(self) -> None:
        """Close the client and transport."""
        if self._initialized:
            self.shutdown()

        if isinstance(self._transport, StdioTransport):
            self._transport.stop()
        elif isinstance(self._transport, (HttpTransport, SseTransport)):
            self._transport.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
