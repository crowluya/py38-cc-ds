"""
Tests for Agent Loop (T021)

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict, List, Optional, Iterator
from unittest.mock import Mock, MagicMock, patch


class TestAgentLoop:
    """Tests for complete agent loop."""

    def test_agent_loop_single_turn(self):
        """Test single turn conversation."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig

        # Mock LLM client
        mock_client = Mock()
        mock_client.chat_completion.return_value = {
            "content": "Hello! How can I help you?",
            "finish_reason": "stop",
        }

        config = AgentLoopConfig(llm_client=mock_client)
        loop = AgentLoop(config)

        response = loop.run_turn("Hello")

        assert response.content == "Hello! How can I help you?"
        assert response.finish_reason == "stop"
        assert not response.has_tool_calls

    def test_agent_loop_with_tool_call(self):
        """Test conversation with tool call."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig
        from deep_code.core.tools.registry import ToolRegistry
        from deep_code.core.tools.base import Tool, ToolResult, ToolParameter, ToolCategory

        # Create a simple test tool
        class EchoTool(Tool):
            @property
            def name(self) -> str:
                return "echo"

            @property
            def description(self) -> str:
                return "Echo the input"

            @property
            def category(self) -> ToolCategory:
                return ToolCategory.UTILITY

            @property
            def parameters(self) -> List[ToolParameter]:
                return [
                    ToolParameter(
                        name="message",
                        type="string",
                        description="Message to echo",
                        required=True,
                    )
                ]

            def execute(self, arguments: Dict[str, Any]) -> ToolResult:
                msg = arguments.get("message", "")
                return ToolResult.success_result(self.name, f"Echo: {msg}")

        registry = ToolRegistry()
        registry.register(EchoTool())

        # Mock LLM client - first call returns tool call, second returns final response
        mock_client = Mock()
        mock_client.chat_completion.side_effect = [
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "echo",
                        "arguments": {"message": "test"},
                    }
                ],
            },
            {
                "content": "The echo tool returned: Echo: test",
                "finish_reason": "stop",
            },
        ]

        config = AgentLoopConfig(
            llm_client=mock_client,
            tool_registry=registry,
        )
        loop = AgentLoop(config)

        response = loop.run_turn("Please echo 'test'")

        assert "Echo: test" in response.content
        assert response.finish_reason == "stop"

    def test_agent_loop_max_tool_rounds(self):
        """Test max tool rounds limit."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig
        from deep_code.core.tools.registry import ToolRegistry
        from deep_code.core.tools.base import Tool, ToolResult, ToolParameter, ToolCategory

        class DummyTool(Tool):
            @property
            def name(self) -> str:
                return "dummy"

            @property
            def description(self) -> str:
                return "Dummy tool"

            @property
            def category(self) -> ToolCategory:
                return ToolCategory.UTILITY

            def execute(self, arguments: Dict[str, Any]) -> ToolResult:
                return ToolResult.success_result(self.name, "done")

        registry = ToolRegistry()
        registry.register(DummyTool())

        # Mock LLM that always returns tool calls
        mock_client = Mock()
        mock_client.chat_completion.return_value = {
            "content": "",
            "finish_reason": "tool_calls",
            "tool_calls": [
                {"id": "call_1", "name": "dummy", "arguments": {}},
            ],
        }

        config = AgentLoopConfig(
            llm_client=mock_client,
            tool_registry=registry,
            max_tool_rounds=3,
        )
        loop = AgentLoop(config)

        response = loop.run_turn("Do something")

        # Should stop after max rounds
        assert mock_client.chat_completion.call_count <= 4  # 3 tool rounds + 1 final

    def test_agent_loop_history_management(self):
        """Test conversation history is maintained."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig

        mock_client = Mock()
        mock_client.chat_completion.return_value = {
            "content": "Response",
            "finish_reason": "stop",
        }

        config = AgentLoopConfig(llm_client=mock_client)
        loop = AgentLoop(config)

        loop.run_turn("First message")
        loop.run_turn("Second message")

        history = loop.get_history()
        assert len(history) == 4  # 2 user + 2 assistant

    def test_agent_loop_reset(self):
        """Test history reset."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig

        mock_client = Mock()
        mock_client.chat_completion.return_value = {
            "content": "Response",
            "finish_reason": "stop",
        }

        config = AgentLoopConfig(llm_client=mock_client)
        loop = AgentLoop(config)

        loop.run_turn("Message")
        assert len(loop.get_history()) == 2

        loop.reset()
        assert len(loop.get_history()) == 0

    def test_agent_loop_system_prompt(self):
        """Test system prompt is included."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig

        mock_client = Mock()
        mock_client.chat_completion.return_value = {
            "content": "Response",
            "finish_reason": "stop",
        }

        config = AgentLoopConfig(
            llm_client=mock_client,
            system_prompt="You are a helpful assistant.",
        )
        loop = AgentLoop(config)

        loop.run_turn("Hello")

        # Check that system prompt was included in the call
        call_args = mock_client.chat_completion.call_args
        messages = call_args[1].get("messages") or call_args[0][0]
        assert messages[0]["role"] == "system"
        assert "helpful assistant" in messages[0]["content"]


class TestAgentLoopStreaming:
    """Tests for streaming support."""

    def test_stream_response(self):
        """Test streaming response."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig

        mock_client = Mock()

        def mock_stream(*args, **kwargs):
            yield {"delta": "Hello"}
            yield {"delta": " "}
            yield {"delta": "World"}

        mock_client.chat_completion_stream.return_value = mock_stream()

        config = AgentLoopConfig(
            llm_client=mock_client,
            stream=True,
        )
        loop = AgentLoop(config)

        chunks = list(loop.run_turn_stream("Hi"))

        assert len(chunks) == 3
        full_content = "".join(c.get("delta", "") for c in chunks)
        assert full_content == "Hello World"

    def test_stream_with_callback(self):
        """Test streaming with callback."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig

        mock_client = Mock()

        def mock_stream(*args, **kwargs):
            yield {"delta": "Hello"}
            yield {"delta": " World"}

        mock_client.chat_completion_stream.return_value = mock_stream()

        received_chunks = []

        def on_chunk(chunk):
            received_chunks.append(chunk)

        config = AgentLoopConfig(
            llm_client=mock_client,
            stream=True,
            on_stream_chunk=on_chunk,
        )
        loop = AgentLoop(config)

        list(loop.run_turn_stream("Hi"))

        assert len(received_chunks) == 2


class TestAgentLoopCallbacks:
    """Tests for callback support."""

    def test_on_tool_start_callback(self):
        """Test tool start callback."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig
        from deep_code.core.tools.registry import ToolRegistry
        from deep_code.core.tools.base import Tool, ToolResult, ToolCategory

        class DummyTool(Tool):
            @property
            def name(self) -> str:
                return "dummy"

            @property
            def description(self) -> str:
                return "Dummy"

            @property
            def category(self) -> ToolCategory:
                return ToolCategory.UTILITY

            def execute(self, arguments: Dict[str, Any]) -> ToolResult:
                return ToolResult.success_result(self.name, "done")

        registry = ToolRegistry()
        registry.register(DummyTool())

        mock_client = Mock()
        mock_client.chat_completion.side_effect = [
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "1", "name": "dummy", "arguments": {}}],
            },
            {"content": "Done", "finish_reason": "stop"},
        ]

        tool_starts = []

        def on_tool_start(tool_name, args):
            tool_starts.append((tool_name, args))

        config = AgentLoopConfig(
            llm_client=mock_client,
            tool_registry=registry,
            on_tool_start=on_tool_start,
        )
        loop = AgentLoop(config)

        loop.run_turn("Do it")

        assert len(tool_starts) == 1
        assert tool_starts[0][0] == "dummy"

    def test_on_tool_end_callback(self):
        """Test tool end callback."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig
        from deep_code.core.tools.registry import ToolRegistry
        from deep_code.core.tools.base import Tool, ToolResult, ToolCategory

        class DummyTool(Tool):
            @property
            def name(self) -> str:
                return "dummy"

            @property
            def description(self) -> str:
                return "Dummy"

            @property
            def category(self) -> ToolCategory:
                return ToolCategory.UTILITY

            def execute(self, arguments: Dict[str, Any]) -> ToolResult:
                return ToolResult.success_result(self.name, "result_data")

        registry = ToolRegistry()
        registry.register(DummyTool())

        mock_client = Mock()
        mock_client.chat_completion.side_effect = [
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "1", "name": "dummy", "arguments": {}}],
            },
            {"content": "Done", "finish_reason": "stop"},
        ]

        tool_ends = []

        def on_tool_end(tool_name, result):
            tool_ends.append((tool_name, result))

        config = AgentLoopConfig(
            llm_client=mock_client,
            tool_registry=registry,
            on_tool_end=on_tool_end,
        )
        loop = AgentLoop(config)

        loop.run_turn("Do it")

        assert len(tool_ends) == 1
        assert tool_ends[0][0] == "dummy"
        assert "result_data" in tool_ends[0][1].output


class TestAgentLoopErrorHandling:
    """Tests for error handling."""

    def test_llm_error_handling(self):
        """Test LLM error is handled gracefully."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopError

        mock_client = Mock()
        mock_client.chat_completion.side_effect = Exception("API Error")

        config = AgentLoopConfig(llm_client=mock_client)
        loop = AgentLoop(config)

        with pytest.raises(AgentLoopError) as exc_info:
            loop.run_turn("Hello")

        assert "API Error" in str(exc_info.value)

    def test_tool_error_handling(self):
        """Test tool error is handled gracefully."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig
        from deep_code.core.tools.registry import ToolRegistry
        from deep_code.core.tools.base import Tool, ToolResult, ToolCategory

        class FailingTool(Tool):
            @property
            def name(self) -> str:
                return "failing"

            @property
            def description(self) -> str:
                return "Always fails"

            @property
            def category(self) -> ToolCategory:
                return ToolCategory.UTILITY

            def execute(self, arguments: Dict[str, Any]) -> ToolResult:
                raise RuntimeError("Tool crashed")

        registry = ToolRegistry()
        registry.register(FailingTool())

        mock_client = Mock()
        mock_client.chat_completion.side_effect = [
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "1", "name": "failing", "arguments": {}}],
            },
            {"content": "Tool failed", "finish_reason": "stop"},
        ]

        config = AgentLoopConfig(
            llm_client=mock_client,
            tool_registry=registry,
        )
        loop = AgentLoop(config)

        # Should not raise, error should be passed to LLM
        response = loop.run_turn("Do it")
        assert response is not None

    def test_unknown_tool_handling(self):
        """Test unknown tool is handled."""
        from deep_code.core.agent_loop import AgentLoop, AgentLoopConfig
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()  # Empty registry

        mock_client = Mock()
        mock_client.chat_completion.side_effect = [
            {
                "content": "",
                "finish_reason": "tool_calls",
                "tool_calls": [{"id": "1", "name": "nonexistent", "arguments": {}}],
            },
            {"content": "Tool not found", "finish_reason": "stop"},
        ]

        config = AgentLoopConfig(
            llm_client=mock_client,
            tool_registry=registry,
        )
        loop = AgentLoop(config)

        # Should not raise
        response = loop.run_turn("Do it")
        assert response is not None


class TestAgentLoopConfig:
    """Tests for AgentLoopConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        from deep_code.core.agent_loop import AgentLoopConfig

        mock_client = Mock()
        config = AgentLoopConfig(llm_client=mock_client)

        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.max_tool_rounds == 10
        assert config.stream is False

    def test_custom_config(self):
        """Test custom configuration."""
        from deep_code.core.agent_loop import AgentLoopConfig

        mock_client = Mock()
        config = AgentLoopConfig(
            llm_client=mock_client,
            max_tokens=2048,
            temperature=0.5,
            max_tool_rounds=5,
            stream=True,
        )

        assert config.max_tokens == 2048
        assert config.temperature == 0.5
        assert config.max_tool_rounds == 5
        assert config.stream is True
