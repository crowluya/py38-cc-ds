"""
Tests for core/tools/registry.py

Python 3.8.10 compatible
"""

import pytest
from typing import Dict, Any, List

from claude_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from claude_code.core.tools.registry import (
    ToolRegistry,
    ToolNotFoundError,
    ToolAlreadyRegisteredError,
    get_default_registry,
)


class EchoTool(Tool):
    """Simple echo tool for testing."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echo a message"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="message", type="string", description="Message to echo", required=True),
        ]

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult.success_result(self.name, arguments.get("message", ""))


class ReadFileTool(Tool):
    """Mock read file tool for testing."""

    @property
    def name(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "Read a file"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="file_path", type="string", description="Path to file", required=True),
        ]

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult.success_result(self.name, f"Content of {arguments.get('file_path', '')}")


class BashTool(Tool):
    """Mock bash tool for testing."""

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute shell command"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SHELL

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="command", type="string", description="Command to execute", required=True),
        ]

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult.success_result(self.name, f"Executed: {arguments.get('command', '')}")


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = EchoTool()
        registry.register(tool)

        retrieved = registry.get("echo")
        assert retrieved is tool
        assert retrieved.name == "echo"

    def test_register_duplicate_raises(self):
        registry = ToolRegistry()
        tool1 = EchoTool()
        tool2 = EchoTool()

        registry.register(tool1)
        with pytest.raises(ToolAlreadyRegisteredError):
            registry.register(tool2)

    def test_register_duplicate_with_replace(self):
        registry = ToolRegistry()
        tool1 = EchoTool()
        tool2 = EchoTool()

        registry.register(tool1)
        registry.register(tool2, replace=True)  # Should not raise

        assert registry.get("echo") is tool2

    def test_get_not_found(self):
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError):
            registry.get("nonexistent")

    def test_has(self):
        registry = ToolRegistry()
        registry.register(EchoTool())

        assert registry.has("echo") is True
        assert registry.has("nonexistent") is False

    def test_unregister(self):
        registry = ToolRegistry()
        registry.register(EchoTool())

        assert registry.has("echo") is True
        registry.unregister("echo")
        assert registry.has("echo") is False

    def test_unregister_not_found(self):
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError):
            registry.unregister("nonexistent")

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())
        registry.register(BashTool())

        tools = registry.list_tools()
        assert len(tools) == 3
        names = [t.name for t in tools]
        assert "echo" in names
        assert "read" in names
        assert "bash" in names

    def test_list_tools_by_category(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())
        registry.register(BashTool())

        file_tools = registry.list_tools(category=ToolCategory.FILE)
        assert len(file_tools) == 1
        assert file_tools[0].name == "read"

        shell_tools = registry.list_tools(category=ToolCategory.SHELL)
        assert len(shell_tools) == 1
        assert shell_tools[0].name == "bash"

    def test_list_names(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())

        names = registry.list_names()
        assert "echo" in names
        assert "read" in names

    def test_get_tools_schema(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())

        schemas = registry.get_tools_schema()
        assert len(schemas) == 2

        # Check schema format
        for schema in schemas:
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_get_tools_schema_specific_tools(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())
        registry.register(BashTool())

        schemas = registry.get_tools_schema(tools=["echo", "bash"])
        assert len(schemas) == 2
        names = [s["function"]["name"] for s in schemas]
        assert "echo" in names
        assert "bash" in names
        assert "read" not in names

    def test_enable_disable(self):
        registry = ToolRegistry()
        registry.register(EchoTool())

        assert registry.is_enabled("echo") is True
        assert registry.is_disabled("echo") is False

        registry.disable("echo")
        assert registry.is_enabled("echo") is False
        assert registry.is_disabled("echo") is True

        registry.enable("echo")
        assert registry.is_enabled("echo") is True
        assert registry.is_disabled("echo") is False

    def test_disabled_tools_excluded_from_list(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())

        registry.disable("echo")

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "read"

        # Include disabled
        tools_all = registry.list_tools(include_disabled=True)
        assert len(tools_all) == 2

    def test_disabled_tools_excluded_from_schema(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())

        registry.disable("echo")

        schemas = registry.get_tools_schema()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "read"

        # Include disabled
        schemas_all = registry.get_tools_schema(include_disabled=True)
        assert len(schemas_all) == 2

    def test_enable_disable_not_found(self):
        registry = ToolRegistry()

        with pytest.raises(ToolNotFoundError):
            registry.enable("nonexistent")

        with pytest.raises(ToolNotFoundError):
            registry.disable("nonexistent")

    def test_get_by_category(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())
        registry.register(BashTool())

        utility_tools = registry.get_by_category(ToolCategory.UTILITY)
        assert len(utility_tools) == 1
        assert utility_tools[0].name == "echo"

    def test_count(self):
        registry = ToolRegistry()
        assert registry.count() == 0

        registry.register(EchoTool())
        registry.register(ReadFileTool())
        assert registry.count() == 2

        registry.disable("echo")
        assert registry.count() == 1
        assert registry.count(include_disabled=True) == 2

    def test_clear(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())
        registry.disable("echo")

        registry.clear()
        assert registry.count() == 0
        assert registry.count(include_disabled=True) == 0

    def test_len(self):
        registry = ToolRegistry()
        assert len(registry) == 0

        registry.register(EchoTool())
        assert len(registry) == 1

        registry.disable("echo")
        assert len(registry) == 0

    def test_contains(self):
        registry = ToolRegistry()
        registry.register(EchoTool())

        assert "echo" in registry
        assert "nonexistent" not in registry

    def test_iter(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(ReadFileTool())

        names = [t.name for t in registry]
        assert "echo" in names
        assert "read" in names


class TestDefaultRegistry:
    """Tests for default registry functions."""

    def test_get_default_registry(self):
        registry1 = get_default_registry()
        registry2 = get_default_registry()
        assert registry1 is registry2  # Same instance

    def test_default_registry_is_tool_registry(self):
        registry = get_default_registry()
        assert isinstance(registry, ToolRegistry)
