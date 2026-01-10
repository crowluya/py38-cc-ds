"""
Output tests - Rich terminal output wrapper

TDD: 测试先行
"""

from io import StringIO

import pytest
from rich.console import Console

from deep_code.cli.output import Output, get_output, set_output


def test_output_create() -> None:
    """验证 Output 可创建"""
    output = Output()
    assert output is not None
    assert output.console is not None


def test_output_with_injected_console() -> None:
    """验证可注入 Console（用于测试）"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)
    output = Output(console=console)

    output.print_text("test")

    # 验证输出被捕获
    result = string_io.getvalue()
    assert "test" in result


def test_print_markdown() -> None:
    """验证 Markdown 渲染"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)
    output = Output(console=console)

    output.print_markdown("# Hello World\n\n**bold** text")

    result = string_io.getvalue()
    assert "Hello World" in result


def test_print_code() -> None:
    """验证代码块高亮"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)
    output = Output(console=console)

    output.print_code("print('hello')", language="python")

    result = string_io.getvalue()
    assert "print" in result


def test_print_panel() -> None:
    """验证面板显示"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)
    output = Output(console=console)

    output.print_panel("content", title="Title")

    result = string_io.getvalue()
    assert "content" in result


def test_print_table() -> None:
    """验证表格显示"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)
    output = Output(console=console)

    output.print_table(
        data=[["a1", "b1"], ["a2", "b2"]],
        headers=["A", "B"]
    )

    result = string_io.getvalue()
    assert "a1" in result
    assert "b1" in result


def test_print_error() -> None:
    """验证错误消息"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)
    output = Output(console=console)

    output.print_error("test error")

    result = string_io.getvalue()
    assert "Error" in result
    assert "test error" in result


def test_print_warning() -> None:
    """验证警告消息"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)
    output = Output(console=console)

    output.print_warning("test warning")

    result = string_io.getvalue()
    assert "Warning" in result
    assert "test warning" in result


def test_print_success() -> None:
    """验证成功消息"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)
    output = Output(console=console)

    output.print_success("test success")

    result = string_io.getvalue()
    assert "✓" in result
    assert "test success" in result


def test_get_output_singleton() -> None:
    """验证默认单例"""
    output1 = get_output()
    output2 = get_output()
    # 应该返回同一个实例
    assert output1 is output2


def test_set_output() -> None:
    """验证设置默认输出"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)
    custom_output = Output(console=console)

    set_output(custom_output)
    result = get_output()

    assert result is custom_output
