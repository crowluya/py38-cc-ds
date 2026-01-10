"""
MCP (Model Context Protocol) Extensions

Python 3.8.10 compatible
Implements MCP client for connecting to MCP servers.
"""

from deep_code.extensions.mcp.protocol import (
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPNotification,
    MCPError,
    ErrorCode,
    encode_message,
    decode_message,
    create_request,
    create_response,
    create_notification,
    create_error_response,
)

__all__ = [
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "MCPError",
    "ErrorCode",
    "encode_message",
    "decode_message",
    "create_request",
    "create_response",
    "create_notification",
    "create_error_response",
]
