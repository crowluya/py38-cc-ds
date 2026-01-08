"""
CLI tests - click command tree

TDD: 测试先行
"""

import sys
from typing import List
from click.testing import CliRunner


def test_cli_module_exists() -> None:
    """验证 CLI 模块存在"""
    from claude_code.cli import main

    assert main is not None


def test_cli_help() -> None:
    """验证 CLI --help 工作"""
    from claude_code.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Claude Code" in result.output
    assert "--help" in result.output


def test_cli_version() -> None:
    """验证 CLI --version 工作"""
    from claude_code.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_chat_command() -> None:
    """验证 chat 子命令存在"""
    from claude_code.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["chat", "--help"])

    assert result.exit_code == 0
    assert "chat" in result.output.lower()


def test_cli_print_command() -> None:
    """验证 print 子命令存在（headless 模式）"""
    from claude_code.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["print", "--help"])

    assert result.exit_code == 0
    assert "print" in result.output.lower()
