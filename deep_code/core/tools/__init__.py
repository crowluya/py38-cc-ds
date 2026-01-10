"""
Tools package for DeepCode

Python 3.8.10 compatible
"""

from deep_code.core.tools.base import (
    Tool,
    ToolCall,
    ToolCategory,
    ToolError,
    ToolParameter,
    ToolPermissionError,
    ToolResult,
    ToolValidationError,
)
from deep_code.core.tools.registry import (
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
