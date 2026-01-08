"""
Terminal output wrapper using Rich

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import json
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel


class Output:
    """
    Terminal output wrapper using Rich.

    Provides:
    - Markdown rendering
    - Code block syntax highlighting
    - Panel display
    - Table display
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize Output wrapper.

        Args:
            console: Rich Console instance (for testing/injection)
        """
        self._console = console or Console()

    @property
    def console(self) -> Console:
        """Get the underlying Console instance."""
        return self._console

    def print_markdown(self, text: str) -> None:
        """
        Print Markdown formatted text.

        Args:
            text: Markdown text to render
        """
        markdown = Markdown(text)
        self._console.print(markdown)

    def print_code(self, code: str, language: str = "python") -> None:
        """
        Print code block with syntax highlighting.

        Args:
            code: Code to display
            language: Programming language for syntax highlighting
        """
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self._console.print(syntax)

    def print_panel(self, content: str, title: str = "", border_style: str = "blue") -> None:
        """
        Print content in a panel.

        Args:
            content: Panel content
            title: Optional panel title
            border_style: Border color/style
        """
        panel = Panel(content, title=title, border_style=border_style)
        self._console.print(panel)

    def print_table(self, data: List[List[str]], headers: List[str]) -> None:
        """
        Print data as a table.

        Args:
            data: Table data (list of rows)
            headers: Column headers
        """
        from rich.table import Table

        table = Table(show_header=True, header_style="bold magenta")
        for header in headers:
            table.add_column(header)

        for row in data:
            table.add_row(*row)

        self._console.print(table)

    def print_text(self, text: str) -> None:
        """
        Print plain text.

        Args:
            text: Text to print
        """
        self._console.print(text)

    def print_error(self, message: str) -> None:
        """
        Print error message.

        Args:
            message: Error message
        """
        self._console.print(f"[bold red]Error:[/bold red] {message}")

    def print_warning(self, message: str) -> None:
        """
        Print warning message.

        Args:
            message: Warning message
        """
        self._console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def print_success(self, message: str) -> None:
        """
        Print success message.

        Args:
            message: Success message
        """
        self._console.print(f"[bold green]✓[/bold green] {message}")


# Default singleton (can be replaced for testing)
_default_output: Optional[Output] = None


def get_output() -> Output:
    """Get the default Output instance."""
    global _default_output
    if _default_output is None:
        _default_output = Output()
    return _default_output


def set_output(output: Output) -> None:
    """Set the default Output instance (for testing)."""
    global _default_output
    _default_output = output


# ===== T091: JSON Output Format =====


def format_json_output(
    content: str,
    finish_reason: str = "stop",
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    timestamp: Optional[str] = None,
) -> str:
    """
    Format response as JSON for programmatic integration.

    Args:
        content: Response content
        finish_reason: Reason for finishing (stop, length, content_filter, etc.)
        tool_calls: List of tool calls made (if any)
        timestamp: ISO format timestamp (defaults to current time)

    Returns:
        JSON string with all required fields

    Schema:
    {
        "content": str,
        "finish_reason": str,
        "tool_calls": List[Dict] | None,
        "timestamp": str (ISO 8601)
    }
    """
    if timestamp is None:
        # Python 3.8 compatible ISO format (without 'Z' suffix)
        timestamp = datetime.utcnow().isoformat()

    output_dict = {
        "content": content,
        "finish_reason": finish_reason,
        "tool_calls": tool_calls,
        "timestamp": timestamp,
    }

    return json.dumps(output_dict, ensure_ascii=False)


def format_json_stream_chunk(
    content: Optional[str] = None,
    done: bool = False,
    finish_reason: Optional[str] = None,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Format a streaming JSON chunk.

    Args:
        content: Content chunk (partial)
        done: Whether this is the final chunk
        finish_reason: Finish reason (only in final chunk when done=True)
        tool_calls: Tool calls (only in final chunk when done=True)

    Returns:
        JSON string per line (newline-delimited JSON)

    Schema for content chunks:
    {
        "content": str,
        "done": false
    }

    Schema for final chunk:
    {
        "done": true,
        "finish_reason": str,
        "tool_calls": List[Dict] | None
    }
    """
    if done:
        # Final chunk
        chunk_dict = {
            "done": True,
        }
        if finish_reason is not None:
            chunk_dict["finish_reason"] = finish_reason
        if tool_calls is not None:
            chunk_dict["tool_calls"] = tool_calls
    else:
        # Content chunk
        chunk_dict = {
            "content": content or "",
            "done": False,
        }

    return json.dumps(chunk_dict, ensure_ascii=False)


def format_tool_calls_for_json(tool_calls: Any) -> List[Dict[str, Any]]:
    """
    Convert tool calls to JSON-serializable format.

    Args:
        tool_calls: Tool calls from ConversationTurn

    Returns:
        List of tool call dictionaries
    """
    if tool_calls is None:
        return None

    # If already a list of dicts, return as-is
    if isinstance(tool_calls, list):
        if not tool_calls:
            return None
        # Check if first element is a dict
        if isinstance(tool_calls[0], dict):
            return tool_calls

        # Convert ToolCall objects to dicts
        result = []
        for tc in tool_calls:
            # Handle ToolCall objects
            if hasattr(tc, "tool_type"):
                result.append({
                    "tool_type": tc.tool_type.value if hasattr(tc.tool_type, "value") else str(tc.tool_type),
                    "command": tc.command,
                    "arguments": tc.arguments,
                    "call_id": tc.call_id,
                })
            else:
                # Fallback for other types
                result.append(dict(tc))
        return result

    return None
