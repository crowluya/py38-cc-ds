"""
MCP stdio Transport - Local Process Communication

Python 3.8.10 compatible
Implements stdio transport for MCP servers running as local processes.
"""

import os
import subprocess
import threading
import queue
from typing import Callable, Dict, List, Optional

from deep_code.extensions.mcp.protocol import (
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPNotification,
    encode_message,
    decode_message,
)


class StdioTransport:
    """
    stdio transport for MCP servers.
    
    Communicates with MCP server via stdin/stdout.
    """

    def __init__(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
    ) -> None:
        """
        Initialize stdio transport.

        Args:
            command: Command to execute
            args: Command arguments
            env: Environment variables
            working_dir: Working directory
        """
        self._command = command
        self._args = args or []
        self._env = env or {}
        self._working_dir = working_dir or os.getcwd()
        
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._message_queue: queue.Queue = queue.Queue()
        self._running = False
        self._on_message: Optional[Callable[[MCPMessage], None]] = None

    def start(self) -> None:
        """Start the MCP server process."""
        if self._running:
            raise RuntimeError("Transport already started")

        # Prepare environment
        process_env = os.environ.copy()
        process_env.update(self._env)

        # Start process
        cmd_list = [self._command] + self._args
        self._process = subprocess.Popen(
            cmd_list,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._working_dir,
            env=process_env,
            universal_newlines=False,  # Use bytes
        )

        self._running = True

        # Start reader thread
        self._reader_thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
        )
        self._reader_thread.start()

    def stop(self) -> None:
        """Stop the MCP server process."""
        if not self._running:
            return

        self._running = False

        # Terminate process
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

        # Wait for reader thread
        if self._reader_thread:
            self._reader_thread.join(timeout=2)

    def send(self, message: MCPMessage) -> None:
        """
        Send a message to the MCP server.

        Args:
            message: Message to send
        """
        if not self._running or not self._process:
            raise RuntimeError("Transport not started")

        # Encode message
        json_str = encode_message(message)
        
        # Send with newline delimiter
        data = (json_str + "\n").encode("utf-8")
        
        try:
            self._process.stdin.write(data)
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise RuntimeError(f"Failed to send message: {e}")

    def receive(self, timeout: Optional[float] = None) -> Optional[MCPMessage]:
        """
        Receive a message from the MCP server.

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

    def _read_loop(self) -> None:
        """Read messages from stdout in background thread."""
        if not self._process or not self._process.stdout:
            return

        # Use readline for line-based protocol (more efficient than chunked read)
        while self._running:
            try:
                # Read one line at a time (blocks until newline or EOF)
                line = self._process.stdout.readline()
                if not line:
                    # EOF reached
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    # Decode and parse message
                    json_str = line.decode("utf-8")
                    message = decode_message(json_str)

                    # Queue message
                    self._message_queue.put(message)

                    # Call handler if set
                    if self._on_message:
                        self._on_message(message)

                except (ValueError, UnicodeDecodeError):
                    # Log error but continue
                    pass

            except Exception:
                # Stop on error
                break

    def is_running(self) -> bool:
        """Check if transport is running."""
        return self._running and self._process is not None and self._process.poll() is None

    def get_stderr(self) -> str:
        """Get stderr output from process."""
        if not self._process or not self._process.stderr:
            return ""

        try:
            stderr_bytes = self._process.stderr.read()
            return stderr_bytes.decode("utf-8", errors="replace")
        except Exception:
            return ""
