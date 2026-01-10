"""
Tool Display for CLI

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides formatting and display utilities for tool calls and results.
"""

import os
from typing import Optional

from claude_code.cli.models import ToolBlock
from claude_code.core.tools.base import ToolCall, ToolResult


def format_tool_call_title(tool_call: ToolCall) -> str:
    """
    Format a tool call into a display title.

    Args:
        tool_call: The tool call to format

    Returns:
        Formatted title string (e.g., "Read(file.py)")
    """
    name = tool_call.name
    args = tool_call.arguments

    # Format based on tool type
    if name == "Read":
        file_path = args.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else ""
        return f"Read({filename})" if filename else "Read()"

    if name == "Write":
        file_path = args.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else ""
        return f"Write({filename})" if filename else "Write()"

    if name == "Edit":
        file_path = args.get("file_path", "")
        filename = os.path.basename(file_path) if file_path else ""
        return f"Edit({filename})" if filename else "Edit()"

    if name == "Bash":
        command = args.get("command", "")
        # Truncate long commands
        if len(command) > 50:
            command = command[:47] + "..."
        return f"Bash({command})"

    if name == "Glob":
        pattern = args.get("pattern", "")
        return f"Glob({pattern})"

    if name == "Grep":
        pattern = args.get("pattern", "")
        # Truncate long patterns
        if len(pattern) > 30:
            pattern = pattern[:27] + "..."
        return f"Grep({pattern})"

    # Default format for unknown tools
    return f"{name}()"


def format_tool_result_body(
    result: ToolResult,
    max_length: int = 5000,
) -> str:
    """
    Format a tool result into display body text.

    Args:
        result: The tool result to format
        max_length: Maximum length of output (truncate if longer)

    Returns:
        Formatted body string
    """
    if result.success:
        body = result.output or ""
    else:
        body = result.error or result.output or "Unknown error"

    # Truncate if too long
    if len(body) > max_length:
        truncated_lines = body[:max_length].rsplit("\n", 1)[0]
        remaining = len(body) - len(truncated_lines)
        body = truncated_lines + f"\n... ({remaining} chars truncated)"

    return body


def create_tool_block(
    tool_call: ToolCall,
    result: ToolResult,
    expanded: bool = False,
    max_lines: int = 12,
) -> ToolBlock:
    """
    Create a ToolBlock from a tool call and its result.

    Args:
        tool_call: The tool call
        result: The tool result
        expanded: Whether to show expanded view
        max_lines: Maximum lines when collapsed

    Returns:
        ToolBlock for display
    """
    title = format_tool_call_title(tool_call)
    body = format_tool_result_body(result)

    return ToolBlock(
        title=title,
        body=body,
        ok=result.success,
        expanded=expanded,
        max_lines=max_lines,
    )


def render_tool_execution(
    tool_call: ToolCall,
    result: ToolResult,
    expanded: bool = False,
) -> str:
    """
    Render a tool execution as formatted text.

    Args:
        tool_call: The tool call
        result: The tool result
        expanded: Whether to show expanded view

    Returns:
        Rendered string with ANSI colors
    """
    block = create_tool_block(tool_call, result, expanded=expanded)
    return block.render()
