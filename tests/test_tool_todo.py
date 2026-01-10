"""
Tests for TodoWrite tool (T013)

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict, List

from deep_code.core.tools.base import ToolCategory, ToolResult


class TestTodoWriteTool:
    """Tests for TodoWriteTool."""

    def test_properties(self):
        """Test tool properties."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        assert tool.name == "TodoWrite"
        assert "task" in tool.description.lower() or "todo" in tool.description.lower()
        assert len(tool.parameters) >= 1
        assert tool.requires_permission is False
        assert tool.is_dangerous is False
        assert tool.category == ToolCategory.UTILITY

    def test_json_schema(self):
        """Test JSON schema generation."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "TodoWrite"
        assert "todos" in schema["function"]["parameters"]["properties"]

    def test_add_single_todo(self):
        """Test adding a single todo item."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        result = tool.execute({
            "todos": [
                {
                    "content": "Implement feature X",
                    "status": "pending",
                    "activeForm": "Implementing feature X",
                }
            ]
        })

        assert result.success is True
        todos = tool.get_todos()
        assert len(todos) == 1
        assert todos[0]["content"] == "Implement feature X"
        assert todos[0]["status"] == "pending"

    def test_add_multiple_todos(self):
        """Test adding multiple todo items."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        result = tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Working on Task 1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "Working on Task 2"},
                {"content": "Task 3", "status": "completed", "activeForm": "Completing Task 3"},
            ]
        })

        assert result.success is True
        todos = tool.get_todos()
        assert len(todos) == 3

    def test_update_todo_status(self):
        """Test updating todo status."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()

        # Add initial todo
        tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Working on Task 1"},
            ]
        })

        # Update status
        result = tool.execute({
            "todos": [
                {"content": "Task 1", "status": "completed", "activeForm": "Completing Task 1"},
            ]
        })

        assert result.success is True
        todos = tool.get_todos()
        assert len(todos) == 1
        assert todos[0]["status"] == "completed"

    def test_replace_all_todos(self):
        """Test that execute replaces all todos."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()

        # Add initial todos
        tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "pending", "activeForm": "Task 2"},
            ]
        })

        # Replace with new todos
        result = tool.execute({
            "todos": [
                {"content": "New Task", "status": "in_progress", "activeForm": "New Task"},
            ]
        })

        assert result.success is True
        todos = tool.get_todos()
        assert len(todos) == 1
        assert todos[0]["content"] == "New Task"

    def test_clear_todos(self):
        """Test clearing all todos."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()

        # Add todos
        tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
            ]
        })

        # Clear by passing empty list
        result = tool.execute({"todos": []})

        assert result.success is True
        todos = tool.get_todos()
        assert len(todos) == 0

    def test_invalid_status(self):
        """Test that invalid status is rejected."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        result = tool.execute({
            "todos": [
                {"content": "Task 1", "status": "invalid_status", "activeForm": "Task 1"},
            ]
        })

        assert result.success is False
        assert "status" in result.error.lower()

    def test_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()

        # Missing content
        result = tool.execute({
            "todos": [
                {"status": "pending", "activeForm": "Task 1"},
            ]
        })
        assert result.success is False

        # Missing status
        result = tool.execute({
            "todos": [
                {"content": "Task 1", "activeForm": "Task 1"},
            ]
        })
        assert result.success is False

        # Missing activeForm
        result = tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending"},
            ]
        })
        assert result.success is False

    def test_get_pending_todos(self):
        """Test getting pending todos."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "Task 2"},
                {"content": "Task 3", "status": "completed", "activeForm": "Task 3"},
            ]
        })

        pending = tool.get_todos_by_status("pending")
        assert len(pending) == 1
        assert pending[0]["content"] == "Task 1"

    def test_get_in_progress_todos(self):
        """Test getting in_progress todos."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "Task 2"},
                {"content": "Task 3", "status": "completed", "activeForm": "Task 3"},
            ]
        })

        in_progress = tool.get_todos_by_status("in_progress")
        assert len(in_progress) == 1
        assert in_progress[0]["content"] == "Task 2"

    def test_get_completed_todos(self):
        """Test getting completed todos."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "Task 2"},
                {"content": "Task 3", "status": "completed", "activeForm": "Task 3"},
            ]
        })

        completed = tool.get_todos_by_status("completed")
        assert len(completed) == 1
        assert completed[0]["content"] == "Task 3"


class TestTodoWriteToolFormatting:
    """Tests for TodoWriteTool output formatting."""

    def test_format_todos_for_display(self):
        """Test formatting todos for display."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "Task 2"},
                {"content": "Task 3", "status": "completed", "activeForm": "Task 3"},
            ]
        })

        formatted = tool.format_todos()
        assert "Task 1" in formatted
        assert "Task 2" in formatted
        assert "Task 3" in formatted
        assert "pending" in formatted.lower() or "[ ]" in formatted
        assert "in_progress" in formatted.lower() or "[~]" in formatted
        assert "completed" in formatted.lower() or "[x]" in formatted

    def test_format_empty_todos(self):
        """Test formatting empty todo list."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()
        formatted = tool.format_todos()
        assert "no" in formatted.lower() or "empty" in formatted.lower()


class TestTodoWriteToolPersistence:
    """Tests for TodoWriteTool persistence."""

    def test_todos_persist_across_calls(self):
        """Test that todos persist across multiple execute calls."""
        from deep_code.core.tools.todo import TodoWriteTool

        tool = TodoWriteTool()

        # First call
        tool.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
            ]
        })

        # Second call - should replace
        tool.execute({
            "todos": [
                {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
                {"content": "Task 2", "status": "pending", "activeForm": "Task 2"},
            ]
        })

        todos = tool.get_todos()
        assert len(todos) == 2
        assert todos[0]["status"] == "completed"

    def test_shared_state_between_instances(self):
        """Test that state can be shared between instances via session."""
        from deep_code.core.tools.todo import TodoWriteTool, TodoSession

        session = TodoSession()
        tool1 = TodoWriteTool(session=session)
        tool2 = TodoWriteTool(session=session)

        # Add via tool1
        tool1.execute({
            "todos": [
                {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
            ]
        })

        # Read via tool2
        todos = tool2.get_todos()
        assert len(todos) == 1
        assert todos[0]["content"] == "Task 1"


class TestTodoWriteToolIntegration:
    """Integration tests for TodoWriteTool."""

    def test_register_with_registry(self):
        """Test registering TodoWriteTool with registry."""
        from deep_code.core.tools.todo import TodoWriteTool
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = TodoWriteTool()
        registry.register(tool)

        assert registry.has("TodoWrite")
        retrieved = registry.get("TodoWrite")
        assert retrieved is tool

    def test_execute_via_executor(self):
        """Test executing TodoWriteTool via ToolExecutor."""
        from deep_code.core.tools.todo import TodoWriteTool
        from deep_code.core.tools.base import ToolCall
        from deep_code.core.tools.registry import ToolRegistry
        from deep_code.core.tool_executor import ToolExecutor

        registry = ToolRegistry()
        tool = TodoWriteTool()
        registry.register(tool)

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_1",
            name="TodoWrite",
            arguments={
                "todos": [
                    {"content": "Test task", "status": "pending", "activeForm": "Testing"},
                ]
            },
        )

        result = executor.execute(tool_call)

        assert result.success is True
        assert len(tool.get_todos()) == 1
