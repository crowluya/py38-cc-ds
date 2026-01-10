"""
MCP SSE Transport - Server-Sent Events Communication

Python 3.8.10 compatible
Implements SSE transport for MCP servers with streaming support.
"""

import json
import threading
import queue
from typing import Callable, Dict, Optional

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
)


class SseTransport:
    """
    SSE (Server-Sent Events) transport for MCP servers.
    
    Maintains a persistent connection for receiving server events.
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> None:
        """
        Initialize SSE transport.

        Args:
            url: MCP server SSE endpoint URL
            headers: Optional HTTP headers (e.g., Authorization)
            timeout: Connection timeout in seconds
        """
        if requests is None:
            raise RuntimeError("requests library not available. Install with: pip install requests")

        self._url = url
        self._headers = headers or {}
        self._timeout = timeout
        
        self._session: Optional[requests.Session] = None
        self._stream_thread: Optional[threading.Thread] = None
        self._message_queue: queue.Queue = queue.Queue()
        self._running = False
        self._on_message: Optional[Callable[[MCPMessage], None]] = None

    def start(self) -> None:
        """Start the SSE connection."""
        if self._running:
            raise RuntimeError("Transport already started")

        self._session = requests.Session()
        
        # Set headers
        self._session.headers.update({
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        })
        
        if self._headers:
            self._session.headers.update(self._headers)

        self._running = True

        # Start stream reader thread
        self._stream_thread = threading.Thread(
            target=self._read_stream,
            daemon=True,
        )
        self._stream_thread.start()

    def stop(self) -> None:
        """Stop the SSE connection."""
        if not self._running:
            return

        self._running = False

        # Close session
        if self._session:
            self._session.close()

        # Wait for stream thread
        if self._stream_thread:
            self._stream_thread.join(timeout=2)

    def receive(self, timeout: Optional[float] = None) -> Optional[MCPMessage]:
        """
        Receive a message from the SSE stream.

        Args:
            timeout: Timeout in seconds (None for blocking)

        Returns:
            MCPMessage or None if timeout
        """
        try:
            return self._message_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def set_message_handler(
        self,
        handler: Callable[[MCPMessage], None],
    ) -> None:
        """
        Set callback for incoming messages.

        Args:
            handler: Callback function
        """
        self._on_message = handler

    def _read_stream(self) -> None:
        """Read SSE stream in background thread."""
        if not self._session:
            return

        try:
            # Open SSE connection
            response = self._session.get(
                self._url,
                stream=True,
                timeout=self._timeout,
            )
            
            if response.status_code != 200:
                return

            # Read event stream
            event_data = ""
            
            for line in response.iter_lines(decode_unicode=True):
                if not self._running:
                    break

                if line is None:
                    continue

                line = line.strip()

                # Empty line indicates end of event
                if not line:
                    if event_data:
                        self._process_event(event_data)
                        event_data = ""
                    continue

                # Parse SSE format
                if line.startswith("data:"):
                    data = line[5:].strip()
                    event_data += data
                elif line.startswith(":"):
                    # Comment, ignore
                    pass
                elif line.startswith("event:"):
                    # Event type, ignore for now
                    pass
                elif line.startswith("id:"):
                    # Event ID, ignore for now
                    pass
                elif line.startswith("retry:"):
                    # Retry interval, ignore for now
                    pass

        except Exception:
            # Stop on error
            pass

    def _process_event(self, data: str) -> None:
        """Process an SSE event."""
        try:
            # Parse JSON message
            message = decode_message(data)

            # Queue message
            self._message_queue.put(message)

            # Call handler if set
            if self._on_message:
                self._on_message(message)

        except Exception:
            # Ignore parse errors
            pass

    def is_running(self) -> bool:
        """Check if transport is running."""
        return self._running

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
