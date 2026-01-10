"""
MCP Protocol Foundation - JSON-RPC 2.0 Messages

Python 3.8.10 compatible
Implements Model Context Protocol (MCP) message types and encoding/decoding.
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


# Base class without dataclass to avoid field ordering issues
class MCPMessage:
    """Base class for MCP messages (JSON-RPC 2.0)."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """Create from dictionary."""
        raise NotImplementedError


@dataclass
class MCPRequest(MCPMessage):
    """MCP request message."""

    method: str
    params: Optional[Dict[str, Any]] = None
    id: Union[str, int] = field(default_factory=lambda: str(uuid.uuid4()))
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
        }
        if self.params is not None:
            result["params"] = self.params
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """Create from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data["method"],
            params=data.get("params"),
            id=data.get("id", str(uuid.uuid4())),
        )


@dataclass
class MCPResponse(MCPMessage):
    """MCP response message."""

    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }
        if self.error is not None:
            result["error"] = self.error
        else:
            result["result"] = self.result
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPResponse":
        """Create from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data["id"],
            result=data.get("result"),
            error=data.get("error"),
        )

    @property
    def is_error(self) -> bool:
        """Check if response is an error."""
        return self.error is not None


@dataclass
class MCPNotification(MCPMessage):
    """MCP notification message (no response expected)."""

    method: str
    params: Optional[Dict[str, Any]] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.params is not None:
            result["params"] = self.params
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPNotification":
        """Create from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data["method"],
            params=data.get("params"),
        )


@dataclass
class MCPError:
    """MCP error object."""

    code: int
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPError":
        """Create from dictionary."""
        return cls(
            code=data["code"],
            message=data["message"],
            data=data.get("data"),
        )


# Standard JSON-RPC 2.0 error codes
class ErrorCode:
    """Standard JSON-RPC 2.0 error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific error codes (application-defined: -32000 to -32099)
    SERVER_ERROR = -32000
    CONNECTION_ERROR = -32001
    TIMEOUT_ERROR = -32002


def encode_message(message: MCPMessage) -> str:
    """
    Encode MCP message to JSON string.

    Args:
        message: MCPMessage to encode

    Returns:
        JSON string
    """
    return json.dumps(message.to_dict(), ensure_ascii=False)


def decode_message(data: str) -> Union[MCPRequest, MCPResponse, MCPNotification]:
    """
    Decode JSON string to MCP message.

    Args:
        data: JSON string

    Returns:
        MCPRequest, MCPResponse, or MCPNotification

    Raises:
        json.JSONDecodeError: If data is not valid JSON
        ValueError: If message type cannot be determined
    """
    obj = json.loads(data)

    # Check if it's a response (has 'result' or 'error')
    if "result" in obj or "error" in obj:
        return MCPResponse.from_dict(obj)

    # Check if it's a request (has 'id')
    if "id" in obj:
        return MCPRequest.from_dict(obj)

    # Otherwise it's a notification
    return MCPNotification.from_dict(obj)


def create_request(method: str, params: Optional[Dict[str, Any]] = None) -> MCPRequest:
    """
    Create a new MCP request.

    Args:
        method: Method name
        params: Optional parameters

    Returns:
        MCPRequest
    """
    return MCPRequest(method=method, params=params)


def create_response(
    request_id: Union[str, int],
    result: Optional[Any] = None,
    error: Optional[MCPError] = None,
) -> MCPResponse:
    """
    Create a new MCP response.

    Args:
        request_id: ID from the request
        result: Result data (if successful)
        error: Error object (if failed)

    Returns:
        MCPResponse
    """
    error_dict = error.to_dict() if error else None
    return MCPResponse(id=request_id, result=result, error=error_dict)


def create_notification(
    method: str,
    params: Optional[Dict[str, Any]] = None,
) -> MCPNotification:
    """
    Create a new MCP notification.

    Args:
        method: Method name
        params: Optional parameters

    Returns:
        MCPNotification
    """
    return MCPNotification(method=method, params=params)


def create_error_response(
    request_id: Union[str, int],
    code: int,
    message: str,
    data: Optional[Any] = None,
) -> MCPResponse:
    """
    Create an error response.

    Args:
        request_id: ID from the request
        code: Error code
        message: Error message
        data: Optional error data

    Returns:
        MCPResponse with error
    """
    error = MCPError(code=code, message=message, data=data)
    return create_response(request_id, error=error)
