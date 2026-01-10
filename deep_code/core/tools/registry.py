"""
Tool registry for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from typing import Any, Dict, List, Optional, Set

from deep_code.core.tools.base import Tool, ToolCategory, ToolError


class ToolNotFoundError(ToolError):
    """Tool not found in registry."""

    def __init__(self, tool_name: str):
        super().__init__(f"Tool not found: {tool_name}", tool_name=tool_name, recoverable=False)


class ToolAlreadyRegisteredError(ToolError):
    """Tool already registered."""

    def __init__(self, tool_name: str):
        super().__init__(f"Tool already registered: {tool_name}", tool_name=tool_name, recoverable=False)


class ToolRegistry:
    """
    Registry for managing tools.

    Provides:
    - Tool registration and lookup
    - Category-based grouping
    - Schema generation for LLM
    - Tool filtering (enabled/disabled)
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._tools: Dict[str, Tool] = {}
        self._disabled: Set[str] = set()

    def register(self, tool: Tool, replace: bool = False) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register
            replace: If True, replace existing tool with same name

        Raises:
            ToolAlreadyRegisteredError: If tool already registered and replace=False
        """
        if tool.name in self._tools and not replace:
            raise ToolAlreadyRegisteredError(tool.name)
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """
        Unregister a tool.

        Args:
            name: Tool name to unregister

        Raises:
            ToolNotFoundError: If tool not found
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)
        del self._tools[name]
        self._disabled.discard(name)

    def get(self, name: str) -> Tool:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance

        Raises:
            ToolNotFoundError: If tool not found
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name]

    def has(self, name: str) -> bool:
        """
        Check if tool exists.

        Args:
            name: Tool name

        Returns:
            True if tool exists
        """
        return name in self._tools

    def list_tools(self, category: Optional[ToolCategory] = None, include_disabled: bool = False) -> List[Tool]:
        """
        List all registered tools.

        Args:
            category: Filter by category (None for all)
            include_disabled: Include disabled tools

        Returns:
            List of Tool instances
        """
        tools = []
        for name, tool in self._tools.items():
            if not include_disabled and name in self._disabled:
                continue
            if category is not None and tool.category != category:
                continue
            tools.append(tool)
        return tools

    def list_names(self, category: Optional[ToolCategory] = None, include_disabled: bool = False) -> List[str]:
        """
        List tool names.

        Args:
            category: Filter by category (None for all)
            include_disabled: Include disabled tools

        Returns:
            List of tool names
        """
        return [t.name for t in self.list_tools(category, include_disabled)]

    def get_tools_schema(self, tools: Optional[List[str]] = None, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        Get OpenAI-compatible tools schema.

        Args:
            tools: List of tool names to include (None for all enabled)
            include_disabled: Include disabled tools

        Returns:
            List of tool schemas in OpenAI format
        """
        schemas = []

        if tools is not None:
            # Specific tools requested
            for name in tools:
                if name in self._tools:
                    if include_disabled or name not in self._disabled:
                        schemas.append(self._tools[name].get_json_schema())
        else:
            # All enabled tools
            for name, tool in self._tools.items():
                if include_disabled or name not in self._disabled:
                    schemas.append(tool.get_json_schema())

        return schemas

    def enable(self, name: str) -> None:
        """
        Enable a tool.

        Args:
            name: Tool name

        Raises:
            ToolNotFoundError: If tool not found
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)
        self._disabled.discard(name)

    def disable(self, name: str) -> None:
        """
        Disable a tool.

        Args:
            name: Tool name

        Raises:
            ToolNotFoundError: If tool not found
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)
        self._disabled.add(name)

    def is_enabled(self, name: str) -> bool:
        """
        Check if tool is enabled.

        Args:
            name: Tool name

        Returns:
            True if tool exists and is enabled
        """
        return name in self._tools and name not in self._disabled

    def is_disabled(self, name: str) -> bool:
        """
        Check if tool is disabled.

        Args:
            name: Tool name

        Returns:
            True if tool exists and is disabled
        """
        return name in self._tools and name in self._disabled

    def get_by_category(self, category: ToolCategory) -> List[Tool]:
        """
        Get tools by category.

        Args:
            category: Tool category

        Returns:
            List of tools in category
        """
        return self.list_tools(category=category)

    def count(self, include_disabled: bool = False) -> int:
        """
        Count registered tools.

        Args:
            include_disabled: Include disabled tools

        Returns:
            Number of tools
        """
        if include_disabled:
            return len(self._tools)
        return len(self._tools) - len(self._disabled)

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._disabled.clear()

    def __len__(self) -> int:
        """Return number of enabled tools."""
        return self.count(include_disabled=False)

    def __contains__(self, name: str) -> bool:
        """Check if tool exists."""
        return self.has(name)

    def __iter__(self):
        """Iterate over enabled tools."""
        for tool in self.list_tools():
            yield tool


# Global default registry
_default_registry: Optional[ToolRegistry] = None


def get_default_registry() -> ToolRegistry:
    """
    Get the default global registry.

    Returns:
        Default ToolRegistry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry


def register_tool(tool: Tool, replace: bool = False) -> None:
    """
    Register a tool in the default registry.

    Args:
        tool: Tool to register
        replace: Replace existing tool
    """
    get_default_registry().register(tool, replace=replace)


def get_tool(name: str) -> Tool:
    """
    Get a tool from the default registry.

    Args:
        name: Tool name

    Returns:
        Tool instance
    """
    return get_default_registry().get(name)
