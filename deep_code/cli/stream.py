"""
Streaming Output Support (T022)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Real-time streaming output for LLM responses
- Formatted rendering with optional colors
- Tool execution progress display
- Progress indicators (spinner, progress bar)
"""

import sys
import threading
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, TextIO

# Try to import colorama for Windows color support
try:
    import colorama
    colorama.init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False


class StreamBuffer:
    """Buffer for accumulating stream chunks."""

    def __init__(self) -> None:
        """Initialize empty buffer."""
        self._chunks: List[str] = []

    def add(self, chunk: str) -> None:
        """
        Add a chunk to the buffer.

        Args:
            chunk: Text chunk to add
        """
        self._chunks.append(chunk)

    def get_content(self) -> str:
        """
        Get accumulated content.

        Returns:
            Combined content string
        """
        return "".join(self._chunks)

    def clear(self) -> None:
        """Clear the buffer."""
        self._chunks = []

    @property
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self._chunks) == 0


class StreamPrinter:
    """Simple stream printer for real-time output."""

    def __init__(
        self,
        output: Optional[TextIO] = None,
        flush: bool = True,
    ) -> None:
        """
        Initialize StreamPrinter.

        Args:
            output: Output stream (default: sys.stdout)
            flush: Whether to flush after each chunk
        """
        self._output = output or sys.stdout
        self._flush = flush
        self._started = False

    def print_chunk(self, chunk: str) -> None:
        """
        Print a chunk to output.

        Args:
            chunk: Text chunk to print
        """
        self._output.write(chunk)
        if self._flush:
            self._output.flush()
        self._started = True

    def finish(self) -> None:
        """Finish streaming with newline."""
        if self._started:
            self._output.write("\n")
            if self._flush:
                self._output.flush()
        self._started = False


class StreamRenderer:
    """
    Formatted stream renderer with optional colors.

    Supports:
    - Colored output (with colorama on Windows)
    - Prefix/suffix formatting
    - Tool execution notifications
    - Error highlighting
    """

    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
    }

    def __init__(
        self,
        output: Optional[TextIO] = None,
        use_color: bool = True,
        prefix: str = "",
        suffix: str = "",
    ) -> None:
        """
        Initialize StreamRenderer.

        Args:
            output: Output stream (default: sys.stdout)
            use_color: Whether to use colors
            prefix: Prefix for output
            suffix: Suffix for output
        """
        self._output = output or sys.stdout
        self._use_color = use_color and self._supports_color()
        self._prefix = prefix
        self._suffix = suffix
        self._started = False
        self._buffer = StreamBuffer()

    def _supports_color(self) -> bool:
        """Check if terminal supports colors."""
        if sys.platform == "win32" and not HAS_COLORAMA:
            return False
        if not hasattr(self._output, "isatty"):
            return False
        return self._output.isatty()

    def _color(self, name: str) -> str:
        """Get color code if colors enabled."""
        if self._use_color:
            return self.COLORS.get(name, "")
        return ""

    def start(self) -> None:
        """Start rendering."""
        if self._prefix:
            self._output.write(self._color("cyan"))
            self._output.write(self._prefix)
            self._output.write(self._color("reset"))
            self._output.flush()
        self._started = True

    def render_chunk(self, chunk: str) -> None:
        """
        Render a text chunk.

        Args:
            chunk: Text chunk to render
        """
        if not self._started:
            self.start()

        self._output.write(chunk)
        self._output.flush()
        self._buffer.add(chunk)

    def finish(self) -> None:
        """Finish rendering."""
        if self._suffix:
            self._output.write(self._suffix)

        self._output.write("\n")
        self._output.flush()
        self._started = False

    def render_tool_start(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """
        Render tool start notification.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
        """
        self._output.write(self._color("dim"))
        self._output.write(f"\n[Tool: {tool_name}]")

        # Show key arguments
        if arguments:
            args_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in list(arguments.items())[:3])
            self._output.write(f" ({args_str})")

        self._output.write(self._color("reset"))
        self._output.write("\n")
        self._output.flush()

    def render_tool_end(self, tool_name: str, result: Any) -> None:
        """
        Render tool end notification.

        Args:
            tool_name: Name of the tool
            result: Tool result
        """
        success = getattr(result, "success", True)
        color = "green" if success else "red"
        status = "OK" if success else "FAILED"

        self._output.write(self._color(color))
        self._output.write(f"[{tool_name}: {status}]")
        self._output.write(self._color("reset"))
        self._output.write("\n")
        self._output.flush()

    def render_error(self, message: str) -> None:
        """
        Render error message.

        Args:
            message: Error message
        """
        self._output.write(self._color("red"))
        self._output.write(self._color("bold"))
        self._output.write(f"Error: {message}")
        self._output.write(self._color("reset"))
        self._output.write("\n")
        self._output.flush()

    def render_info(self, message: str) -> None:
        """
        Render info message.

        Args:
            message: Info message
        """
        self._output.write(self._color("cyan"))
        self._output.write(message)
        self._output.write(self._color("reset"))
        self._output.write("\n")
        self._output.flush()

    def get_content(self) -> str:
        """Get accumulated content."""
        return self._buffer.get_content()


class StreamCallbackAdapter:
    """Adapter to convert stream chunks to callbacks."""

    def __init__(
        self,
        callback: Optional[Callable[[Any], None]] = None,
        extract_delta: bool = False,
    ) -> None:
        """
        Initialize adapter.

        Args:
            callback: Callback function to call with chunks
            extract_delta: Whether to extract delta from chunk dict
        """
        self._callback = callback
        self._extract_delta = extract_delta

    def on_chunk(self, chunk: Any) -> None:
        """
        Handle a stream chunk.

        Args:
            chunk: Stream chunk
        """
        if self._callback is None:
            return

        if self._extract_delta and isinstance(chunk, dict):
            delta = chunk.get("delta", "")
            if delta:
                self._callback(delta)
        else:
            self._callback(chunk)


class Spinner:
    """Simple spinner for progress indication."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    # Fallback for terminals without unicode
    FRAMES_ASCII = ["|", "/", "-", "\\"]

    def __init__(
        self,
        output: Optional[TextIO] = None,
        message: str = "",
        use_unicode: bool = True,
    ) -> None:
        """
        Initialize spinner.

        Args:
            output: Output stream
            message: Message to display
            use_unicode: Whether to use unicode frames
        """
        self._output = output or sys.stdout
        self._message = message
        self._frames = self.FRAMES if use_unicode else self.FRAMES_ASCII
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_idx = 0

    def start(self) -> None:
        """Start the spinner."""
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the spinner."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        # Clear the spinner line
        self._output.write("\r" + " " * (len(self._message) + 5) + "\r")
        self._output.flush()

    def _spin(self) -> None:
        """Spin animation loop."""
        while self._running:
            frame = self._frames[self._frame_idx % len(self._frames)]
            self._output.write(f"\r{frame} {self._message}")
            self._output.flush()
            self._frame_idx += 1
            time.sleep(0.1)


class ProgressBar:
    """Simple progress bar."""

    def __init__(
        self,
        output: Optional[TextIO] = None,
        total: int = 100,
        width: int = 40,
        fill: str = "█",
        empty: str = "░",
    ) -> None:
        """
        Initialize progress bar.

        Args:
            output: Output stream
            total: Total value (100%)
            width: Bar width in characters
            fill: Fill character
            empty: Empty character
        """
        self._output = output or sys.stdout
        self._total = total
        self._width = width
        self._fill = fill
        self._empty = empty
        self._current = 0

    def update(self, value: int) -> None:
        """
        Update progress.

        Args:
            value: Current value
        """
        self._current = value
        self._render()

    def increment(self, amount: int = 1) -> None:
        """
        Increment progress.

        Args:
            amount: Amount to increment
        """
        self._current += amount
        self._render()

    def _render(self) -> None:
        """Render the progress bar."""
        if self._total <= 0:
            percent = 100
        else:
            percent = min(100, int(self._current * 100 / self._total))

        filled = int(self._width * percent / 100)
        bar = self._fill * filled + self._empty * (self._width - filled)

        self._output.write(f"\r[{bar}] {percent}%")
        self._output.flush()

    def finish(self) -> None:
        """Finish progress bar."""
        self._current = self._total
        self._render()
        self._output.write("\n")
        self._output.flush()


def stream_to_renderer(
    stream: Iterator[Dict[str, Any]],
    renderer: StreamRenderer,
) -> str:
    """
    Stream chunks to a renderer.

    Args:
        stream: Iterator of stream chunks
        renderer: Renderer to use

    Returns:
        Accumulated content
    """
    renderer.start()

    for chunk in stream:
        if isinstance(chunk, dict):
            delta = chunk.get("delta", "")
        else:
            delta = getattr(chunk, "delta", str(chunk))

        if delta:
            renderer.render_chunk(delta)

    renderer.finish()
    return renderer.get_content()


def create_stream_handler(
    output: Optional[TextIO] = None,
    use_color: bool = True,
    prefix: str = "",
) -> StreamRenderer:
    """
    Create a stream handler for agent loop integration.

    Args:
        output: Output stream
        use_color: Whether to use colors
        prefix: Output prefix

    Returns:
        StreamRenderer configured as handler
    """
    renderer = StreamRenderer(
        output=output,
        use_color=use_color,
        prefix=prefix,
    )

    # Add on_chunk method for compatibility
    def on_chunk(chunk: Any) -> None:
        if isinstance(chunk, dict):
            delta = chunk.get("delta", "")
        else:
            delta = getattr(chunk, "delta", str(chunk))
        if delta:
            renderer.render_chunk(delta)

    renderer.on_chunk = on_chunk  # type: ignore
    return renderer
