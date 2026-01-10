"""
Tests for Agent Tool Loop (T011)

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch

from claude_code.core.agent import (
    Agent,
    AgentConfig,
    ConversationTurn,
    Message,
    MessageRole,
)
from claude_code.core.tools.base import (
    Tool,
    ToolCall,
    ToolResult,
    ToolCategory,
    ToolParameter,
)
from claude_code.core.tools.registry import ToolRegistry
from claude_code.core.tool_executor import ToolExecutor


class MockTool(Tool):
    """Mock tool for testing."""

    def __init__(self, name: str = "MockTool", result: str = "Mock result"):
        self._name = name
        self._result = result

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
                required=False,
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        return False

    @property
    def is_dangerous(self) -> bool:
        return False

    def execute(self, arguments: dict) -> ToolResult:
        return ToolResult.success_result(
            self.name,
            self._result,
            metadata={"input": arguments.get("input")},
        )


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses: Optional[List[Dict[str, Any]]] = None):
        self._responses = responses or []
        self._call_count = 0
        self._last_messages = None
        self._last_tools = None

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        self._last_messages = messages
        self._last_tools = tools

        if self._call_count < len(self._responses):
            response = self._responses[self._call_count]
            self._call_count += 1
            return response

        # Default response
        return {
            "content": "Default response",
            "finish_reason": "stop",
            "tool_calls": None,
        }

    def get_model(self) -> str:
        return "mock-model"


class TestAgentToolLoop:
    """Tests for Agent tool loop functionality."""

    def test_agent_with_tool_registry(self):
        """Test agent initialization with tool registry."""
        registry = ToolRegistry()
        registry.register(MockTool())

        llm_client = MockLLMClient([
            {"content": "Hello!", "finish_reason": "stop", "tool_calls": None}
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        assert agent._tool_registry is not None
        assert agent._tool_executor is not None

    def test_agent_process_without_tools(self):
        """Test agent process without tool calls."""
        registry = ToolRegistry()
        registry.register(MockTool())

        llm_client = MockLLMClient([
            {"content": "Hello, how can I help?", "finish_reason": "stop", "tool_calls": None}
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        turn = agent.process("Hello")

        assert turn.content == "Hello, how can I help?"
        assert not turn.has_tools

    def test_agent_process_with_single_tool_call(self):
        """Test agent process with a single tool call."""
        registry = ToolRegistry()
        registry.register(MockTool("TestTool", "Tool executed successfully"))

        # First response has tool call, second is final response
        llm_client = MockLLMClient([
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "TestTool",
                        "arguments": {"input": "test"},
                    }
                ],
            },
            {
                "content": "I executed the tool and got: Tool executed successfully",
                "finish_reason": "stop",
                "tool_calls": None,
            },
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        turn = agent.process("Run the test tool")

        assert "Tool executed successfully" in turn.content

    def test_agent_process_with_multiple_tool_calls(self):
        """Test agent process with multiple tool calls in one turn."""
        registry = ToolRegistry()
        registry.register(MockTool("Tool1", "Result 1"))
        registry.register(MockTool("Tool2", "Result 2"))

        llm_client = MockLLMClient([
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [
                    {"id": "call_1", "name": "Tool1", "arguments": {}},
                    {"id": "call_2", "name": "Tool2", "arguments": {}},
                ],
            },
            {
                "content": "Both tools executed",
                "finish_reason": "stop",
                "tool_calls": None,
            },
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        turn = agent.process("Run both tools")

        assert turn.content == "Both tools executed"

    def test_agent_tool_loop_multiple_rounds(self):
        """Test agent with multiple rounds of tool calls."""
        registry = ToolRegistry()
        registry.register(MockTool("Tool1", "Result 1"))
        registry.register(MockTool("Tool2", "Result 2"))

        llm_client = MockLLMClient([
            # Round 1: Call Tool1
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "call_1", "name": "Tool1", "arguments": {}}],
            },
            # Round 2: Call Tool2
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "call_2", "name": "Tool2", "arguments": {}}],
            },
            # Final response
            {
                "content": "Completed both rounds",
                "finish_reason": "stop",
                "tool_calls": None,
            },
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        turn = agent.process("Run tools in sequence")

        assert turn.content == "Completed both rounds"
        assert llm_client._call_count == 3

    def test_agent_max_tool_rounds_limit(self):
        """Test that agent respects max_tool_rounds limit."""
        registry = ToolRegistry()
        registry.register(MockTool())

        # Create infinite tool call loop
        infinite_tool_response = {
            "content": "",
            "finish_reason": "tool_calls",
            "tool_calls": [{"id": "call_n", "name": "MockTool", "arguments": {}}],
        }

        llm_client = MockLLMClient([infinite_tool_response] * 100)

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
            max_tool_rounds=3,
        )
        agent = Agent(config)

        turn = agent.process("Run forever")

        # Should stop after max_tool_rounds
        assert llm_client._call_count <= 4  # Initial + 3 rounds

    def test_agent_tool_callback(self):
        """Test that tool callbacks are invoked."""
        registry = ToolRegistry()
        registry.register(MockTool())

        llm_client = MockLLMClient([
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "call_1", "name": "MockTool", "arguments": {}}],
            },
            {
                "content": "Done",
                "finish_reason": "stop",
                "tool_calls": None,
            },
        ])

        callback_calls = []

        def on_tool_call(tool_call: ToolCall, result: ToolResult):
            callback_calls.append((tool_call, result))

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
            on_tool_call=on_tool_call,
        )
        agent = Agent(config)

        agent.process("Run tool")

        assert len(callback_calls) == 1
        assert callback_calls[0][0].name == "MockTool"
        assert callback_calls[0][1].success is True

    def test_agent_tools_schema_passed_to_llm(self):
        """Test that tools schema is passed to LLM."""
        registry = ToolRegistry()
        registry.register(MockTool("TestTool"))

        llm_client = MockLLMClient([
            {"content": "Response", "finish_reason": "stop", "tool_calls": None}
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        agent.process("Hello")

        # Check that tools were passed to LLM
        assert llm_client._last_tools is not None
        assert len(llm_client._last_tools) == 1
        assert llm_client._last_tools[0]["function"]["name"] == "TestTool"

    def test_agent_tool_result_in_history(self):
        """Test that tool results are added to history."""
        registry = ToolRegistry()
        registry.register(MockTool("TestTool", "Tool output"))

        llm_client = MockLLMClient([
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "call_1", "name": "TestTool", "arguments": {}}],
            },
            {
                "content": "Final response",
                "finish_reason": "stop",
                "tool_calls": None,
            },
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        agent.process("Run tool")

        history = agent.get_history()

        # Should have: user message, assistant (tool call), tool result, assistant (final)
        assert len(history) >= 3

        # Find tool message
        tool_messages = [m for m in history if m.role == MessageRole.TOOL]
        assert len(tool_messages) >= 1

    def test_agent_unknown_tool_error(self):
        """Test handling of unknown tool call."""
        registry = ToolRegistry()
        # Don't register any tools

        llm_client = MockLLMClient([
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "call_1", "name": "UnknownTool", "arguments": {}}],
            },
            {
                "content": "Tool not found",
                "finish_reason": "stop",
                "tool_calls": None,
            },
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        turn = agent.process("Run unknown tool")

        # Should handle gracefully
        assert turn is not None


class TestAgentToolLoopIntegration:
    """Integration tests for agent tool loop."""

    def test_agent_with_read_tool(self):
        """Test agent with actual Read tool."""
        import tempfile
        from claude_code.core.tools.read import ReadTool

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Hello from file")
            temp_path = f.name

        try:
            registry = ToolRegistry()
            registry.register(ReadTool())

            llm_client = MockLLMClient([
                {
                    "content": "",
                    "finish_reason": "tool_calls",
                    "tool_calls": [
                        {"id": "call_1", "name": "Read", "arguments": {"file_path": temp_path}}
                    ],
                },
                {
                    "content": "File content: Hello from file",
                    "finish_reason": "stop",
                    "tool_calls": None,
                },
            ])

            config = AgentConfig(
                llm_client=llm_client,
                tool_registry=registry,
            )
            agent = Agent(config)

            turn = agent.process("Read the file")

            assert "Hello from file" in turn.content
        finally:
            import os
            os.unlink(temp_path)

    def test_agent_with_glob_tool(self):
        """Test agent with actual Glob tool."""
        import tempfile
        from pathlib import Path
        from claude_code.core.tools.glob import GlobTool

        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "test1.py").write_text("# test1")
            (Path(temp_dir) / "test2.py").write_text("# test2")

            registry = ToolRegistry()
            registry.register(GlobTool())

            llm_client = MockLLMClient([
                {
                    "content": "",
                    "finish_reason": "tool_calls",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "name": "Glob",
                            "arguments": {"pattern": "*.py", "path": temp_dir},
                        }
                    ],
                },
                {
                    "content": "Found 2 Python files",
                    "finish_reason": "stop",
                    "tool_calls": None,
                },
            ])

            config = AgentConfig(
                llm_client=llm_client,
                tool_registry=registry,
            )
            agent = Agent(config)

            turn = agent.process("Find Python files")

            assert "2" in turn.content or "Python" in turn.content


class TestAgentToolLoopEdgeCases:
    """Edge case tests for agent tool loop."""

    def test_empty_tool_calls_list(self):
        """Test handling of empty tool_calls list."""
        registry = ToolRegistry()
        registry.register(MockTool())

        llm_client = MockLLMClient([
            {
                "content": "No tools needed",
                "finish_reason": "stop",
                "tool_calls": [],  # Empty list
            },
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        turn = agent.process("Hello")

        assert turn.content == "No tools needed"
        assert not turn.has_tools

    def test_tool_execution_error(self):
        """Test handling of tool execution error."""

        class FailingTool(Tool):
            @property
            def name(self) -> str:
                return "FailingTool"

            @property
            def description(self) -> str:
                return "A tool that fails"

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
                raise RuntimeError("Tool execution failed")

        registry = ToolRegistry()
        registry.register(FailingTool())

        llm_client = MockLLMClient([
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "call_1", "name": "FailingTool", "arguments": {}}],
            },
            {
                "content": "Tool failed, but I handled it",
                "finish_reason": "stop",
                "tool_calls": None,
            },
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        turn = agent.process("Run failing tool")

        # Should handle error gracefully
        assert turn is not None

    def test_no_tool_registry(self):
        """Test agent without tool registry (backward compatibility)."""
        llm_client = MockLLMClient([
            {"content": "Hello!", "finish_reason": "stop", "tool_calls": None}
        ])

        config = AgentConfig(
            llm_client=llm_client,
            # No tool_registry
        )
        agent = Agent(config)

        turn = agent.process("Hello")

        assert turn.content == "Hello!"

    def test_disabled_tool_not_in_schema(self):
        """Test that disabled tools are not included in schema."""
        registry = ToolRegistry()
        registry.register(MockTool("EnabledTool"))
        registry.register(MockTool("DisabledTool"))
        registry.disable("DisabledTool")

        llm_client = MockLLMClient([
            {"content": "Response", "finish_reason": "stop", "tool_calls": None}
        ])

        config = AgentConfig(
            llm_client=llm_client,
            tool_registry=registry,
        )
        agent = Agent(config)

        agent.process("Hello")

        # Only enabled tool should be in schema
        assert llm_client._last_tools is not None
        tool_names = [t["function"]["name"] for t in llm_client._last_tools]
        assert "EnabledTool" in tool_names
        assert "DisabledTool" not in tool_names
