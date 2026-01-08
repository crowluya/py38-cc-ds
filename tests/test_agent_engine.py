"""
Agent Engine tests - Conversation loop and tool orchestration

TDD: 测试先行
"""

from typing import List, Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from claude_code.core.agent import (
    Agent,
    AgentConfig,
    ToolCall,
    ToolType,
    create_agent,
    ConversationTurn,
)


# ===== T060: Agent basic conversation loop tests =====


def test_agent_create() -> None:
    """验证创建 Agent"""
    mock_llm = MagicMock()
    config = AgentConfig(llm_client=mock_llm)

    agent = Agent(config)
    assert agent is not None


def test_agent_create_convenience() -> None:
    """验证便捷函数 create_agent"""
    mock_llm = MagicMock()
    agent = create_agent(mock_llm)

    assert agent is not None


def test_agent_process_prompt() -> None:
    """验证处理用户提示"""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = MagicMock(
        content="Hello!",
        finish_reason="stop",
    )

    config = AgentConfig(llm_client=mock_llm)
    agent = Agent(config)

    response = agent.process("Hello")

    assert "Hello" in response.content
    assert response.finish_reason == "stop"


def test_agent_conversation_history() -> None:
    """验证对话历史维护"""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = MagicMock(
        content="Response",
        finish_reason="stop",
    )

    config = AgentConfig(llm_client=mock_llm)
    agent = Agent(config)

    agent.process("First message")
    agent.process("Second message")

    history = agent.get_history()

    # Should have: user msg, assistant response, user msg, assistant response
    assert len(history) >= 4


def test_agent_with_system_prompt() -> None:
    """验证带系统提示的 Agent"""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = MagicMock(
        content="OK",
        finish_reason="stop",
    )

    config = AgentConfig(
        llm_client=mock_llm,
        system_prompt="You are a helpful assistant."
    )
    agent = Agent(config)

    agent.process("Hello")

    # Check that system prompt was included
    call_args = mock_llm.chat_completion.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")

    assert messages[0]["role"] == "system"
    assert "helpful assistant" in messages[0]["content"].lower()


def test_agent_with_context_injection() -> None:
    """验证上下文注入"""
    from tempfile import TemporaryDirectory
    from pathlib import Path

    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = MagicMock(
        content="Got it",
        finish_reason="stop",
    )

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("File content", encoding="utf-8")

        config = AgentConfig(llm_client=mock_llm)
        agent = Agent(config)

        # Inject context
        agent.inject_context(f"@{test_file}")

        # Process a message
        agent.process("Summarize the file")

        # Check context was included
        call_args = mock_llm.chat_completion.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")

        # Should have system prompt, context, and user message
        content_text = " ".join([m.get("content", "") for m in messages])
        assert str(test_file) in content_text


def test_agent_reset() -> None:
    """验证重置对话"""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = MagicMock(
        content="Response",
        finish_reason="stop",
    )

    config = AgentConfig(llm_client=mock_llm)
    agent = Agent(config)

    agent.process("First")
    agent.process("Second")

    # Should have history
    assert len(agent.get_history()) > 0

    # Reset
    agent.reset()

    # History should be cleared
    assert len(agent.get_history()) == 0


def test_conversation_turn_result() -> None:
    """验证 ConversationTurn 结果"""
    turn = ConversationTurn(
        content="Hello there",
        finish_reason="stop",
        tool_calls=None,
    )

    assert turn.content == "Hello there"
    assert turn.finish_reason == "stop"
    assert turn.tool_calls is None
    assert turn.has_tools is False


def test_conversation_turn_with_tools() -> None:
    """验证带工具调用的对话回合"""
    tool_call = ToolCall(
        tool_type=ToolType.SHELL,
        command="ls",
        arguments={},
    )

    turn = ConversationTurn(
        content="",
        finish_reason="tool_calls",
        tool_calls=[tool_call],
    )

    assert turn.has_tools is True
    assert turn.tool_calls[0].command == "ls"


def test_agent_config_defaults() -> None:
    """验证 AgentConfig 默认值"""
    mock_llm = MagicMock()
    config = AgentConfig(llm_client=mock_llm)

    assert config.llm_client == mock_llm
    assert config.max_tokens == 4096
    assert config.temperature == 0.7
    assert config.system_prompt is None


# ===== T061: Tool orchestration tests =====


def test_tool_call_create() -> None:
    """验证创建 ToolCall"""
    tool = ToolCall(
        tool_type=ToolType.SHELL,
        command="ls -la",
        arguments={},
    )

    assert tool.tool_type == ToolType.SHELL
    assert tool.command == "ls -la"


def test_tool_type_read_file() -> None:
    """验证文件读取工具类型"""
    tool = ToolCall(
        tool_type=ToolType.READ_FILE,
        command="/path/to/file.txt",
        arguments={},
    )

    assert tool.tool_type == ToolType.READ_FILE
    assert tool.command == "/path/to/file.txt"


def test_tool_type_read_directory() -> None:
    """验证目录读取工具类型"""
    tool = ToolCall(
        tool_type=ToolType.READ_DIRECTORY,
        command="/path/to/dir",
        arguments={"recursive": True},
    )

    assert tool.tool_type == ToolType.READ_DIRECTORY
    assert tool.arguments["recursive"] is True


def test_agent_execute_tool_shell() -> None:
    """验证执行 shell 工具"""
    mock_llm = MagicMock()

    # First call: request tool, second call: final answer
    mock_llm.chat_completion.side_effect = [
        MagicMock(
            content="",
            finish_reason="tool_calls",
            tool_calls=[
                ToolCall(
                    tool_type=ToolType.SHELL,
                    command="echo test",
                    arguments={},
                )
            ],
        ),
        MagicMock(
            content="Command executed: test",
            finish_reason="stop",
            tool_calls=None,
        ),
    ]

    config = AgentConfig(llm_client=mock_llm)
    agent = Agent(config)

    response = agent.process("Run echo test")

    # Should have tool result in response
    assert "test" in response.content.lower()


def test_agent_execute_tool_read_file() -> None:
    """验证执行读取文件工具"""
    from tempfile import TemporaryDirectory
    from pathlib import Path

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Hello from file", encoding="utf-8")

        mock_llm = MagicMock()
        # First call: request tool, second call: final answer
        mock_llm.chat_completion.side_effect = [
            MagicMock(
                content="",
                finish_reason="tool_calls",
                tool_calls=[
                    ToolCall(
                        tool_type=ToolType.READ_FILE,
                        command=str(test_file),
                        arguments={},
                    )
                ],
            ),
            MagicMock(
                content="File content: Hello from file",
                finish_reason="stop",
                tool_calls=None,
            ),
        ]

        config = AgentConfig(llm_client=mock_llm)
        agent = Agent(config)

        response = agent.process("Read the file")

        # Should have file content in response
        assert "Hello from file" in response.content


def test_agent_execute_tool_read_directory() -> None:
    """验证执行读取目录工具"""
    from tempfile import TemporaryDirectory
    from pathlib import Path

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "file1.txt").write_text("content1")
        Path(tmpdir, "file2.py").write_text("content2")

        mock_llm = MagicMock()
        # First call: request tool, second call: final answer
        mock_llm.chat_completion.side_effect = [
            MagicMock(
                content="",
                finish_reason="tool_calls",
                tool_calls=[
                    ToolCall(
                        tool_type=ToolType.READ_DIRECTORY,
                        command=tmpdir,
                        arguments={"recursive": False},
                    )
                ],
            ),
            MagicMock(
                content="Directory listing shows file1.txt and file2.py",
                finish_reason="stop",
                tool_calls=None,
            ),
        ]

        config = AgentConfig(llm_client=mock_llm)
        agent = Agent(config)

        response = agent.process("List directory")

        # Should have directory info in response
        assert "file1.txt" in response.content or "file2.py" in response.content


def test_agent_multi_tool_execution() -> None:
    """验证多个工具依次执行"""
    mock_llm = MagicMock()

    # First call: request tools
    mock_llm.chat_completion.side_effect = [
        # First response - tool calls
        MagicMock(
            content="",
            finish_reason="tool_calls",
            tool_calls=[
                ToolCall(
                    tool_type=ToolType.SHELL,
                    command="echo first",
                    arguments={},
                ),
                ToolCall(
                    tool_type=ToolType.SHELL,
                    command="echo second",
                    arguments={},
                ),
            ],
        ),
        # Second response - final answer after tools
        MagicMock(
            content="Done with tools",
            finish_reason="stop",
            tool_calls=None,
        ),
    ]

    config = AgentConfig(llm_client=mock_llm)
    agent = Agent(config)

    response = agent.process("Run two commands")

    # Should have final response
    assert "Done with tools" in response.content


def test_agent_tool_execution_error_handling() -> None:
    """验证工具执行错误处理"""
    mock_llm = MagicMock()

    # LLM returns a tool call that will fail
    mock_llm.chat_completion.side_effect = [
        MagicMock(
            content="",
            finish_reason="tool_calls",
            tool_calls=[
                ToolCall(
                    tool_type=ToolType.SHELL,
                    command="nonexistent-command-xyz-123",
                    arguments={},
                )
            ],
        ),
        # Final response after error
        MagicMock(
            content="Command failed",
            finish_reason="stop",
            tool_calls=None,
        ),
    ]

    config = AgentConfig(llm_client=mock_llm)
    agent = Agent(config)

    response = agent.process("Run bad command")

    # Should handle error gracefully
    assert len(response.content) > 0


def test_agent_streaming_response() -> None:
    """验证流式响应处理"""
    mock_llm = MagicMock()

    # Mock streaming response
    def mock_stream():
        yield "Hello"
        yield " there"
        yield "!"

    mock_llm.chat_completion_stream.return_value = [
        MagicMock(content="Hello"),
        MagicMock(content=" there"),
        MagicMock(content="!"),
    ]

    config = AgentConfig(llm_client=mock_llm, stream=True)
    agent = Agent(config)

    response = agent.process("Say hello")

    # Should accumulate streamed content
    assert "Hello there!" in response.content or response.content.count("Hello") > 0


def test_agent_max_tokens_config() -> None:
    """验证最大 token 配置"""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = MagicMock(
        content="OK",
        finish_reason="stop",
    )

    config = AgentConfig(llm_client=mock_llm, max_tokens=1000)
    agent = Agent(config)

    agent.process("Test")

    # Check max_tokens was passed
    call_args = mock_llm.chat_completion.call_args
    kwargs = call_args.kwargs if hasattr(call_args, 'kwargs') else {}

    assert kwargs.get("max_tokens") == 1000


def test_agent_temperature_config() -> None:
    """验证温度配置"""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = MagicMock(
        content="OK",
        finish_reason="stop",
    )

    config = AgentConfig(llm_client=mock_llm, temperature=0.5)
    agent = Agent(config)

    agent.process("Test")

    # Check temperature was passed
    call_args = mock_llm.chat_completion.call_args
    kwargs = call_args.kwargs if hasattr(call_args, 'kwargs') else {}

    assert kwargs.get("temperature") == 0.5
