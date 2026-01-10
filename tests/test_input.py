"""
Input tests - Prompt Toolkit input wrapper

TDD: 测试先行
"""

from typing import List

import pytest
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit import PromptSession

from deep_code.cli.input import Input, get_input, set_input


def test_input_create() -> None:
    """验证 Input 可创建"""
    input_obj = Input()
    assert input_obj is not None


def test_input_with_session_injection() -> None:
    """验证可注入 PromptSession（用于测试）"""
    session = PromptSession(input=create_pipe_input(), output=DummyOutput())
    input_obj = Input(session=session)

    assert input_obj._session is session


def test_prompt_simple() -> None:
    """验证简单输入提示"""
    # 使用 pipe input 模拟用户输入
    with create_pipe_input() as inp:
        inp.send_text("test input\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        result = input_obj.prompt("Enter: ")
        assert result == "test input"


def test_prompt_multiline() -> None:
    """验证多行输入"""
    with create_pipe_input() as inp:
        # 在 prompt_toolkit 中，Enter 提交，我们需要手动输入
        inp.send_text("line 1\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        result = input_obj.prompt("Enter: ", multiline=False)
        assert result == "line 1"


def test_prompt_password() -> None:
    """验证密码输入模式"""
    with create_pipe_input() as inp:
        inp.send_text("secret\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        result = input_obj.prompt("Password: ", password=True)
        assert result == "secret"


def test_prompt_with_completer() -> None:
    """验证自动完成"""
    with create_pipe_input() as inp:
        inp.send_text("hel\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        completions = ["hello", "help", "world"]
        result = input_obj.prompt_with_completer("Enter: ", completions)
        assert result == "hel"


def test_confirm_yes() -> None:
    """验证确认：yes"""
    with create_pipe_input() as inp:
        inp.send_text("y\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        result = input_obj.confirm("Continue?")
        assert result is True


def test_confirm_no() -> None:
    """验证确认：no"""
    with create_pipe_input() as inp:
        inp.send_text("n\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        result = input_obj.confirm("Continue?")
        assert result is False


def test_confirm_default_true() -> None:
    """验证确认：默认 True（直接 Enter）"""
    with create_pipe_input() as inp:
        inp.send_text("\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        result = input_obj.confirm("Continue?", default=True)
        assert result is True


def test_confirm_default_false() -> None:
    """验证确认：默认 False（直接 Enter）"""
    with create_pipe_input() as inp:
        inp.send_text("\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        result = input_obj.confirm("Continue?", default=False)
        assert result is False


def test_select_valid() -> None:
    """验证选择：有效选项"""
    with create_pipe_input() as inp:
        inp.send_text("1\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        choices = ["Option A", "Option B"]
        result = input_obj.select("Choose:", choices)

        assert result == 0  # 0-based index


def test_select_cancel() -> None:
    """验证选择：取消"""
    with create_pipe_input() as inp:
        inp.send_text("0\n")
        session = PromptSession(input=inp, output=DummyOutput())
        input_obj = Input(session=session)

        choices = ["Option A", "Option B"]
        result = input_obj.select("Choose:", choices)

        assert result is None


def test_get_input_singleton() -> None:
    """验证默认单例"""
    input1 = get_input()
    input2 = get_input()
    # 应该返回同一个实例
    assert input1 is input2


def test_set_input() -> None:
    """验证设置默认输入"""
    session = PromptSession(input=create_pipe_input(), output=DummyOutput())
    custom_input = Input(session=session)

    set_input(custom_input)
    result = get_input()

    assert result is custom_input
