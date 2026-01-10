"""
Tests for Tool Executor (T010)

Python 3.8.10 compatible
"""

import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from claude_code.core.tools.base import (
    Tool,
    ToolCall,
    ToolResult,
    ToolCategory,
    ToolParameter,
    ToolError,
)
from claude_code.core.tools.registry import ToolRegistry
from claude_code.core.tool_executor import ToolExecutor


class MockTool(Tool):
    """Mock tool for testing."""

    def __init__(self, name: str = "MockTool", should_fail: bool = False):
        self._name = name
        self._should_fail = should_fail

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.OTHER

    @property
    def parameters(self) -> list:
        return [
            ToolParameter(
                name="input",
                type="string",
                description="Test input",
                required=True,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        return False

    @property
    def is_dangerous(self) -> bool:
        return False

    def execute(self, arguments: dict) -> ToolResult:
        self.validate_arguments(arguments)
        if self._should_fail:
            return ToolResult.error_result(self.name, "Mock failure")
        return ToolResult.success_result(
            self.name,
            f"Executed with input: {arguments.get('input', '')}",
            metadata={"input": arguments.get("input")},
        )


class DangerousMockTool(Tool):
    """Mock dangerous tool for testing."""

    @property
    def name(self) -> str:
        return "DangerousTool"

    @property
    def description(self) -> str:
        return "A dangerous mock tool"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SHELL

    @property
    def parameters(self) -> list:
        return []

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return True

    def execute(self, arguments: dict) -> ToolResult:
        return ToolResult.success_result(self.name, "Dangerous action executed")


class TestToolExecutor:
    """Tests for ToolExecutor."""

    def test_init(self):
        """Test executor initialization."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        assert executor is not None

    def test_execute_single_tool(self):
        """Test executing a single tool call."""
        registry = ToolRegistry()
        registry.register(MockTool())

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_1",
            name="MockTool",
            arguments={"input": "test"},
        )

        result = executor.execute(tool_call)

        assert result.success is True
        assert "test" in result.output

    def test_execute_unknown_tool(self):
        """Test executing unknown tool."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        tool_call = ToolCall(
            id="call_1",
            name="UnknownTool",
            arguments={},
        )

        result = executor.execute(tool_call)

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_execute_tool_failure(self):
        """Test handling tool execution failure."""
        registry = ToolRegistry()
        registry.register(MockTool(should_fail=True))

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_1",
            name="MockTool",
            arguments={"input": "test"},
        )

        result = executor.execute(tool_call)

        assert result.success is False
        assert "failure" in result.error.lower()

    def test_execute_multiple_tools(self):
        """Test executing multiple tool calls."""
        registry = ToolRegistry()
        registry.register(MockTool("Tool1"))
        registry.register(MockTool("Tool2"))

        executor = ToolExecutor(registry)
        tool_calls = [
            ToolCall(id="call_1", name="Tool1", arguments={"input": "first"}),
            ToolCall(id="call_2", name="Tool2", arguments={"input": "second"}),
        ]

        results = executor.execute_all(tool_calls)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True
        assert "first" in results[0].output
        assert "second" in results[1].output

    def test_execute_with_callback(self):
        """Test execution with callback."""
        registry = ToolRegistry()
        registry.register(MockTool())

        callback_calls = []

        def callback(tool_call: ToolCall, result: ToolResult):
            callback_calls.append((tool_call, result))

        executor = ToolExecutor(registry, on_tool_complete=callback)
        tool_call = ToolCall(
            id="call_1",
            name="MockTool",
            arguments={"input": "test"},
        )

        executor.execute(tool_call)

        assert len(callback_calls) == 1
        assert callback_calls[0][0].id == "call_1"
        assert callback_calls[0][1].success is True

    def test_execute_disabled_tool(self):
        """Test executing a disabled tool."""
        registry = ToolRegistry()
        registry.register(MockTool())
        registry.disable("MockTool")

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_1",
            name="MockTool",
            arguments={"input": "test"},
        )

        result = executor.execute(tool_call)

        assert result.success is False
        assert "disabled" in result.error.lower()


class TestToolExecutorPermissions:
    """Tests for ToolExecutor permission handling."""

    def test_dangerous_tool_requires_approval(self):
        """Test that dangerous tools require approval."""
        registry = ToolRegistry()
        registry.register(DangerousMockTool())

        # No approval callback - should fail
        executor = ToolExecutor(registry, require_approval=True)
        tool_call = ToolCall(
            id="call_1",
            name="DangerousTool",
            arguments={},
        )

        result = executor.execute(tool_call)

        assert result.success is False
        assert "permission" in result.error.lower() or "approval" in result.error.lower()

    def test_dangerous_tool_with_approval(self):
        """Test dangerous tool with approval callback."""
        registry = ToolRegistry()
        registry.register(DangerousMockTool())

        def approve_callback(tool_call: ToolCall) -> bool:
            return True  # Always approve

        executor = ToolExecutor(
            registry,
            require_approval=True,
            approval_callback=approve_callback,
        )
        tool_call = ToolCall(
            id="call_1",
            name="DangerousTool",
            arguments={},
        )

        result = executor.execute(tool_call)

        assert result.success is True

    def test_dangerous_tool_denied(self):
        """Test dangerous tool with denied approval."""
        registry = ToolRegistry()
        registry.register(DangerousMockTool())

        def deny_callback(tool_call: ToolCall) -> bool:
            return False  # Always deny

        executor = ToolExecutor(
            registry,
            require_approval=True,
            approval_callback=deny_callback,
        )
        tool_call = ToolCall(
            id="call_1",
            name="DangerousTool",
            arguments={},
        )

        result = executor.execute(tool_call)

        assert result.success is False
        assert "denied" in result.error.lower()

    def test_safe_tool_no_approval_needed(self):
        """Test that safe tools don't need approval."""
        registry = ToolRegistry()
        registry.register(MockTool())

        executor = ToolExecutor(registry, require_approval=True)
        tool_call = ToolCall(
            id="call_1",
            name="MockTool",
            arguments={"input": "test"},
        )

        result = executor.execute(tool_call)

        # Safe tool should execute without approval
        assert result.success is True


class TestToolExecutorLogging:
    """Tests for ToolExecutor logging."""

    def test_execution_logged(self):
        """Test that executions are logged."""
        registry = ToolRegistry()
        registry.register(MockTool())

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_1",
            name="MockTool",
            arguments={"input": "test"},
        )

        executor.execute(tool_call)

        # Check execution history
        history = executor.get_history()
        assert len(history) == 1
        assert history[0]["tool_call"].id == "call_1"
        assert history[0]["result"].success is True

    def test_history_limit(self):
        """Test that history is limited."""
        registry = ToolRegistry()
        registry.register(MockTool())

        executor = ToolExecutor(registry, history_limit=5)

        # Execute more than limit
        for i in range(10):
            tool_call = ToolCall(
                id=f"call_{i}",
                name="MockTool",
                arguments={"input": f"test_{i}"},
            )
            executor.execute(tool_call)

        history = executor.get_history()
        assert len(history) == 5
        # Should keep most recent
        assert history[-1]["tool_call"].id == "call_9"

    def test_clear_history(self):
        """Test clearing history."""
        registry = ToolRegistry()
        registry.register(MockTool())

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_1",
            name="MockTool",
            arguments={"input": "test"},
        )

        executor.execute(tool_call)
        assert len(executor.get_history()) == 1

        executor.clear_history()
        assert len(executor.get_history()) == 0


class TestToolExecutorErrorHandling:
    """Tests for ToolExecutor error handling."""

    def test_tool_exception_caught(self):
        """Test that tool exceptions are caught."""
        registry = ToolRegistry()

        class ExceptionTool(Tool):
            @property
            def name(self) -> str:
                return "ExceptionTool"

            @property
            def description(self) -> str:
                return "Tool that raises exception"

            @property
            def category(self) -> ToolCategory:
                return ToolCategory.OTHER

            @property
            def parameters(self) -> list:
                return []

            @property
            def requires_permission(self) -> bool:
                return False

            @property
            def is_dangerous(self) -> bool:
                return False

            def execute(self, arguments: dict) -> ToolResult:
                raise RuntimeError("Unexpected error")

        registry.register(ExceptionTool())
        executor = ToolExecutor(registry)

        tool_call = ToolCall(
            id="call_1",
            name="ExceptionTool",
            arguments={},
        )

        result = executor.execute(tool_call)

        assert result.success is False
        assert "error" in result.error.lower()

    def test_validation_error_caught(self):
        """Test that validation errors are caught."""
        registry = ToolRegistry()
        registry.register(MockTool())

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_1",
            name="MockTool",
            arguments={},  # Missing required 'input'
        )

        result = executor.execute(tool_call)

        assert result.success is False
        assert "required" in result.error.lower() or "missing" in result.error.lower()


class TestToolExecutorIntegration:
    """Integration tests with real tools."""

    def test_with_read_tool(self):
        """Test executor with Read tool."""
        from claude_code.core.tools.read import ReadTool

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello World")
            temp_path = f.name

        try:
            registry = ToolRegistry()
            registry.register(ReadTool())

            executor = ToolExecutor(registry)
            tool_call = ToolCall(
                id="call_1",
                name="Read",
                arguments={"file_path": temp_path},
            )

            result = executor.execute(tool_call)

            assert result.success is True
            assert "Hello World" in result.output
        finally:
            import os
            os.unlink(temp_path)

    def test_with_write_tool(self):
        """Test executor with Write tool."""
        from claude_code.core.tools.write import WriteTool

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = str(Path(temp_dir) / "test.txt")

            registry = ToolRegistry()
            registry.register(WriteTool())

            executor = ToolExecutor(registry)
            tool_call = ToolCall(
                id="call_1",
                name="Write",
                arguments={
                    "file_path": file_path,
                    "content": "Test content",
                },
            )

            result = executor.execute(tool_call)

            assert result.success is True
            assert Path(file_path).read_text() == "Test content"

    def test_with_glob_tool(self):
        """Test executor with Glob tool."""
        from claude_code.core.tools.glob import GlobTool

        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "test1.py").write_text("# test1")
            (Path(temp_dir) / "test2.py").write_text("# test2")

            registry = ToolRegistry()
            registry.register(GlobTool())

            executor = ToolExecutor(registry)
            tool_call = ToolCall(
                id="call_1",
                name="Glob",
                arguments={
                    "pattern": "*.py",
                    "path": temp_dir,
                },
            )

            result = executor.execute(tool_call)

            assert result.success is True
            assert "test1.py" in result.output
            assert "test2.py" in result.output
