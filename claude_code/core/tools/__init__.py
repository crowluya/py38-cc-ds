"""
Tools package for Claude Code Python MVP

Python 3.8.10 compatible
"""

from claude_code.core.tools.base import (
    Tool,
    ToolCall,
    ToolCategory,
    ToolError,
    ToolParameter,
    ToolPermissionError,
    ToolResult,
    ToolValidationError,
)
from claude_code.core.tools.registry import (
    ToolRegistry,
    ToolNotFoundError,
    ToolAlreadyRegisteredError,
    get_default_registry,
    register_tool,
    get_tool,
)

__all__ = [
    # base
    "Tool",
    "ToolCall",
    "ToolCategory",
    "ToolError",
    "ToolParameter",
    "ToolPermissionError",
    "ToolResult",
    "ToolValidationError",
    # registry
    "ToolRegistry",
    "ToolNotFoundError",
    "ToolAlreadyRegisteredError",
    "get_default_registry",
    "register_tool",
    "get_tool",
]
