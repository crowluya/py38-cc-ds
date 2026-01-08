"""
Agent tests - Command output injection to context

TDD: 测试先行
"""

from typing import Dict, List, Any

import pytest

from claude_code.core.agent import (
    Message,
    MessageRole,
    ToolResult,
    CommandOutputContext,
    inject_command_output,
)


def test_message_create() -> None:
    """验证创建 Message"""
    msg = Message(role=MessageRole.USER, content="Hello")
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello"


def test_message_with_tool_result() -> None:
    """验证带工具结果的 Message"""
    tool_result = ToolResult(
        tool_id="test",
        name="echo",
        output="hello",
        success=True,
    )

    msg = Message(
        role=MessageRole.TOOL,
        content="",
        tool_result=tool_result,
    )

    assert msg.role == MessageRole.TOOL
    assert msg.tool_result.name == "echo"


def test_tool_result_str() -> None:
    """验证 ToolResult 字符串表示"""
    result = ToolResult(
        tool_id="test",
        name="echo",
        output="hello",
        success=True,
    )

    s = str(result)
    assert "echo" in s
    assert "success" in s


def test_command_output_context_create() -> None:
    """验证创建命令输出上下文"""
    context = CommandOutputContext(
        command="echo hello",
        return_code=0,
        stdout="hello\n",
        stderr="",
    )

    assert context.command == "echo hello"
    assert context.return_code == 0
    assert context.stdout == "hello\n"


def test_command_output_context_to_message() -> None:
    """验证命令输出转换为消息"""
    context = CommandOutputContext(
        command="ls -la",
        return_code=0,
        stdout="file1.txt\nfile2.py\n",
        stderr="",
    )

    msg = context.to_message()

    assert msg.role == MessageRole.TOOL
    assert msg.tool_result.name == "shell"
    assert "ls -la" in msg.tool_result.output
    assert "file1.txt" in msg.tool_result.output


def test_command_output_context_with_stderr() -> None:
    """验证包含 stderr 的命令输出上下文"""
    context = CommandOutputContext(
        command="invalid_cmd",
        return_code=127,
        stdout="",
        stderr="command not found",
    )

    msg = context.to_message()

    assert msg.tool_result.success is False
    assert "command not found" in msg.tool_result.output


def test_inject_command_output_to_history() -> None:
    """验证将命令输出注入历史"""
    history: List[Message] = [
        Message(role=MessageRole.USER, content="Run ls"),
    ]

    context = CommandOutputContext(
        command="ls",
        return_code=0,
        stdout="file1.txt\n",
        stderr="",
    )

    new_history = inject_command_output(history, context)

    assert len(new_history) == 2
    assert new_history[0].role == MessageRole.USER
    assert new_history[1].role == MessageRole.TOOL
    assert "file1.txt" in new_history[1].tool_result.output


def test_inject_multiple_commands() -> None:
    """验证注入多个命令输出"""
    history: List[Message] = [
        Message(role=MessageRole.USER, content="Run ls"),
        CommandOutputContext(
            command="ls",
            return_code=0,
            stdout="file1.txt\n",
            stderr="",
        ).to_message(),
        Message(role=MessageRole.USER, content="Run pwd"),
    ]

    context2 = CommandOutputContext(
        command="pwd",
        return_code=0,
        stdout="/home/user\n",
        stderr="",
    )

    new_history = inject_command_output(history, context2)

    assert len(new_history) == 4
    assert new_history[3].role == MessageRole.TOOL
    assert "pwd" in new_history[3].tool_result.output


def test_message_to_dict() -> None:
    """验证 Message 转字典"""
    tool_result = ToolResult(
        tool_id="test",
        name="echo",
        output="hello",
        success=True,
    )

    msg = Message(
        role=MessageRole.TOOL,
        content="",
        tool_result=tool_result,
    )

    d = msg.to_dict()

    assert d["role"] == "tool"
    assert "tool_result" in d
    assert d["tool_result"]["name"] == "echo"


def test_message_from_dict() -> None:
    """验证从字典创建 Message"""
    d: Dict[str, Any] = {
        "role": "user",
        "content": "Hello",
        "tool_result": None,
    }

    msg = Message.from_dict(d)

    assert msg.role == MessageRole.USER
    assert msg.content == "Hello"


def test_message_format_for_llm() -> None:
    """验证为 LLM 格式化消息"""
    msg = Message(
        role=MessageRole.USER,
        content="List files",
    )

    formatted = msg.format_for_llm()

    assert "role" in formatted
    assert "content" in formatted
    assert formatted["content"] == "List files"


def test_tool_result_with_combined_output() -> None:
    """验证工具结果的合并输出"""
    result = ToolResult(
        tool_id="test",
        name="cmd",
        output="stdout here",
        error_output="stderr here",
        success=False,
    )

    combined = result.get_combined_output()

    assert "stdout here" in combined
    assert "stderr here" in combined


def test_command_output_context_format() -> None:
    """验证命令输出上下文格式化"""
    context = CommandOutputContext(
        command="echo test",
        return_code=0,
        stdout="test\n",
        stderr="",
    )

    formatted = context.format()

    assert "echo test" in formatted
    assert "test" in formatted
    assert "exit code: 0" in formatted.lower()


def test_conversation_history_serialization() -> None:
    """验证对话历史序列化"""
    history: List[Message] = [
        Message(role=MessageRole.USER, content="Hello"),
        Message(
            role=MessageRole.ASSISTANT,
            content="Hi there!",
        ),
    ]

    serialized = [msg.to_dict() for msg in history]

    assert len(serialized) == 2
    assert serialized[0]["role"] == "user"
    assert serialized[1]["role"] == "assistant"

    # Round-trip
    restored = [Message.from_dict(d) for d in serialized]

    assert restored[0].content == "Hello"
    assert restored[1].content == "Hi there!"
