"""
Tests for Task tool (T014) - Subagent execution

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch

from claude_code.core.tools.base import ToolCategory, ToolResult


class TestTaskTool:
    """Tests for TaskTool."""

    def test_properties(self):
        """Test tool properties."""
        from claude_code.core.tools.task import TaskTool

        tool = TaskTool()
        assert tool.name == "Task"
        assert "agent" in tool.description.lower() or "task" in tool.description.lower()
        assert len(tool.parameters) >= 2
        assert tool.requires_permission is False
        assert tool.is_dangerous is False
        assert tool.category == ToolCategory.AGENT

    def test_json_schema(self):
        """Test JSON schema generation."""
        from claude_code.core.tools.task import TaskTool

        tool = TaskTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "Task"
        assert "prompt" in schema["function"]["parameters"]["properties"]
        assert "subagent_type" in schema["function"]["parameters"]["properties"]

    def test_execute_simple_task(self):
        """Test executing a simple task."""
        from claude_code.core.tools.task import TaskTool

        # Create mock LLM client
        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "content": "Task completed successfully",
            "finish_reason": "stop",
            "tool_calls": None,
        }

        tool = TaskTool(llm_client=mock_llm)
        result = tool.execute({
            "prompt": "Search for Python files",
            "subagent_type": "Explore",
            "description": "Find Python files",
        })

        assert result.success is True
        assert "completed" in result.output.lower() or len(result.output) > 0

    def test_execute_with_different_agent_types(self):
        """Test executing with different agent types."""
        from claude_code.core.tools.task import TaskTool

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "content": "Done",
            "finish_reason": "stop",
            "tool_calls": None,
        }

        tool = TaskTool(llm_client=mock_llm)

        # Test Explore agent
        result = tool.execute({
            "prompt": "Find files",
            "subagent_type": "Explore",
            "description": "Explore codebase",
        })
        assert result.success is True

        # Test Plan agent
        result = tool.execute({
            "prompt": "Plan implementation",
            "subagent_type": "Plan",
            "description": "Create plan",
        })
        assert result.success is True

        # Test Bash agent
        result = tool.execute({
            "prompt": "Run tests",
            "subagent_type": "Bash",
            "description": "Execute tests",
        })
        assert result.success is True

    def test_execute_missing_prompt(self):
        """Test that missing prompt fails."""
        from claude_code.core.tools.task import TaskTool

        tool = TaskTool()
        result = tool.execute({
            "subagent_type": "Explore",
            "description": "Test",
        })

        assert result.success is False
        assert "prompt" in result.error.lower()

    def test_execute_missing_subagent_type(self):
        """Test that missing subagent_type fails."""
        from claude_code.core.tools.task import TaskTool

        tool = TaskTool()
        result = tool.execute({
            "prompt": "Do something",
            "description": "Test",
        })

        assert result.success is False
        assert "subagent_type" in result.error.lower()

    def test_execute_invalid_subagent_type(self):
        """Test that invalid subagent_type fails."""
        from claude_code.core.tools.task import TaskTool

        tool = TaskTool()
        result = tool.execute({
            "prompt": "Do something",
            "subagent_type": "InvalidType",
            "description": "Test",
        })

        assert result.success is False
        assert "invalid" in result.error.lower() or "subagent_type" in result.error.lower()

    def test_execute_with_max_turns(self):
        """Test executing with max_turns limit."""
        from claude_code.core.tools.task import TaskTool

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "content": "Done",
            "finish_reason": "stop",
            "tool_calls": None,
        }

        tool = TaskTool(llm_client=mock_llm)
        result = tool.execute({
            "prompt": "Complex task",
            "subagent_type": "Explore",
            "description": "Test",
            "max_turns": 5,
        })

        assert result.success is True

    def test_execute_without_llm_client(self):
        """Test executing without LLM client fails gracefully."""
        from claude_code.core.tools.task import TaskTool

        tool = TaskTool()  # No LLM client
        result = tool.execute({
            "prompt": "Do something",
            "subagent_type": "Explore",
            "description": "Test",
        })

        assert result.success is False
        assert "llm" in result.error.lower() or "client" in result.error.lower()


class TestTaskToolAgentTypes:
    """Tests for different agent types."""

    def test_explore_agent_system_prompt(self):
        """Test that Explore agent has appropriate system prompt."""
        from claude_code.core.tools.task import TaskTool, get_agent_system_prompt

        prompt = get_agent_system_prompt("Explore")
        assert "explore" in prompt.lower() or "search" in prompt.lower() or "find" in prompt.lower()

    def test_plan_agent_system_prompt(self):
        """Test that Plan agent has appropriate system prompt."""
        from claude_code.core.tools.task import TaskTool, get_agent_system_prompt

        prompt = get_agent_system_prompt("Plan")
        assert "plan" in prompt.lower() or "design" in prompt.lower()

    def test_bash_agent_system_prompt(self):
        """Test that Bash agent has appropriate system prompt."""
        from claude_code.core.tools.task import TaskTool, get_agent_system_prompt

        prompt = get_agent_system_prompt("Bash")
        assert "bash" in prompt.lower() or "command" in prompt.lower() or "shell" in prompt.lower()

    def test_general_purpose_agent_system_prompt(self):
        """Test that general-purpose agent has appropriate system prompt."""
        from claude_code.core.tools.task import TaskTool, get_agent_system_prompt

        prompt = get_agent_system_prompt("general-purpose")
        assert len(prompt) > 0


class TestTaskToolIntegration:
    """Integration tests for TaskTool."""

    def test_register_with_registry(self):
        """Test registering TaskTool with registry."""
        from claude_code.core.tools.task import TaskTool
        from claude_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = TaskTool()
        registry.register(tool)

        assert registry.has("Task")
        retrieved = registry.get("Task")
        assert retrieved is tool

    def test_execute_via_executor(self):
        """Test executing TaskTool via ToolExecutor."""
        from claude_code.core.tools.task import TaskTool
        from claude_code.core.tools.base import ToolCall
        from claude_code.core.tools.registry import ToolRegistry
        from claude_code.core.tool_executor import ToolExecutor

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "content": "Task result",
            "finish_reason": "stop",
            "tool_calls": None,
        }

        registry = ToolRegistry()
        tool = TaskTool(llm_client=mock_llm)
        registry.register(tool)

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_1",
            name="Task",
            arguments={
                "prompt": "Find Python files",
                "subagent_type": "Explore",
                "description": "Search files",
            },
        )

        result = executor.execute(tool_call)
        assert result.success is True


class TestTaskToolMetadata:
    """Tests for TaskTool metadata."""

    def test_result_includes_metadata(self):
        """Test that result includes useful metadata."""
        from claude_code.core.tools.task import TaskTool

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "content": "Found 5 files",
            "finish_reason": "stop",
            "tool_calls": None,
        }

        tool = TaskTool(llm_client=mock_llm)
        result = tool.execute({
            "prompt": "Find files",
            "subagent_type": "Explore",
            "description": "Search",
        })

        assert result.metadata is not None
        assert "subagent_type" in result.metadata

    def test_result_includes_agent_id(self):
        """Test that result includes agent ID for resumption."""
        from claude_code.core.tools.task import TaskTool

        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "content": "Done",
            "finish_reason": "stop",
            "tool_calls": None,
        }

        tool = TaskTool(llm_client=mock_llm)
        result = tool.execute({
            "prompt": "Task",
            "subagent_type": "Explore",
            "description": "Test",
        })

        assert result.metadata is not None
        # Agent ID should be present for potential resumption
        assert "agent_id" in result.metadata or "task_id" in result.metadata
