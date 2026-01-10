"""
MCP HTTP Transport - Remote Server Communication

Python 3.8.10 compatible
Implements HTTP transport for MCP servers accessible via HTTP.
"""

import json
from typing import Dict, Optional

try:
    import requests
except ImportError:
    requests = None

from deep_code.extensions.mcp.protocol import (
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPNotification,
    encode_message,
    decode_message,
    ErrorCode,
    create_error_response,
)


class HttpTransport:
    """
    HTTP transport for MCP servers.
    
    Communicates with MCP server via HTTP POST requests.
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> None:
        """
        Initialize HTTP transport.

        Args:
            url: MCP server URL
            headers: Optional HTTP headers (e.g., Authorization)
            timeout: Request timeout in seconds
        """
        if requests is None:
            raise RuntimeError("requests library not available. Install with: pip install requests")

        self._url = url
        self._headers = headers or {}
        self._timeout = timeout
        self._session = requests.Session()
        
        # Set default headers
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        
        # Add custom headers
        if self._headers:
            self._session.headers.update(self._headers)

    def send(self, message: MCPMessage) -> MCPResponse:
        """
        Send a message to the MCP server and wait for response.

        Args:
            message: Message to send (MCPRequest or MCPNotification)

        Returns:
            MCPResponse

        Raises:
            RuntimeError: If request fails
        """
        # Encode message
        json_str = encode_message(message)
        
        try:
            # Send POST request
            response = self._session.post(
                self._url,
                data=json_str,
                timeout=self._timeout,
            )
            
            # Check status code
            if response.status_code != 200:
                # Create error response
                if isinstance(message, MCPRequest):
                    return create_error_response(
                        request_id=message.id,
                        code=ErrorCode.SERVER_ERROR,
                        message=f"HTTP {response.status_code}: {response.text}",
                    )
                else:
                    raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
            
            # Parse response
            response_text = response.text
            response_msg = decode_message(response_text)
            
            if not isinstance(response_msg, MCPResponse):
                # Unexpected message type
                if isinstance(message, MCPRequest):
                    return create_error_response(
                        request_id=message.id,
                        code=ErrorCode.INTERNAL_ERROR,
                        message=f"Expected response, got {type(response_msg).__name__}",
                    )
                else:
                    raise RuntimeError(f"Expected response, got {type(response_msg).__name__}")
            
            return response_msg
            
        except requests.exceptions.Timeout:
            if isinstance(message, MCPRequest):
                return create_error_response(
                    request_id=message.id,
                    code=ErrorCode.TIMEOUT_ERROR,
                    message=f"Request timeout after {self._timeout}s",
                )
            else:
                raise RuntimeError(f"Request timeout after {self._timeout}s")
                
        except requests.exceptions.ConnectionError as e:
            if isinstance(message, MCPRequest):
                return create_error_response(
                    request_id=message.id,
                    code=ErrorCode.CONNECTION_ERROR,
                    message=f"Connection error: {e}",
                )
            else:
                raise RuntimeError(f"Connection error: {e}")
                
        except Exception as e:
            if isinstance(message, MCPRequest):
                return create_error_response(
                    request_id=message.id,
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Request failed: {e}",
                )
            else:
                raise RuntimeError(f"Request failed: {e}")

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
