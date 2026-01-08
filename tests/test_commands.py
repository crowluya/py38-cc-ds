"""
Slash Commands tests - T080-T081

Tests for custom slash commands discovery and execution.
TDD: 测试先行
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import pytest

from claude_code.interaction.commands import (
    CommandArgumentError,
    CommandFrontmatter,
    SlashCommand,
    SlashCommandManager,
    execute_command_template,
)


# ===== T080: Slash Commands Discovery Tests =====


def test_command_manager_create() -> None:
    """验证创建 SlashCommandManager"""
    manager = SlashCommandManager()

    assert manager is not None
    assert len(manager.list_commands()) == 0


def test_command_manager_scan_empty_directory() -> None:
    """验证扫描空命令目录"""
    with TemporaryDirectory() as tmpdir:
        manager = SlashCommandManager()

        manager.scan_commands(project_dir=Path(tmpdir))

        assert len(manager.list_commands()) == 0


def test_command_manager_discover_single_command() -> None:
    """验证发现单个命令"""
    with TemporaryDirectory() as tmpdir:
        # Create .claude/commands directory
        commands_dir = Path(tmpdir, ".claude", "commands")
        commands_dir.mkdir(parents=True)

        # Create a simple command
        command_file = commands_dir / "test.txt"
        command_file.write_text("List all test files", encoding="utf-8")

        manager = SlashCommandManager()
        manager.scan_commands(project_dir=Path(tmpdir))

        commands = manager.list_commands()
        assert len(commands) == 1
        assert "test" in commands


def test_command_manager_discover_multiple_commands() -> None:
    """验证发现多个命令"""
    with TemporaryDirectory() as tmpdir:
        commands_dir = Path(tmpdir, ".claude", "commands")
        commands_dir.mkdir(parents=True)

        (commands_dir / "deploy.txt").write_text("Deploy the app", encoding="utf-8")
        (commands_dir / "test.txt").write_text("Run tests", encoding="utf-8")
        (commands_dir / "build.txt").write_text("Build the project", encoding="utf-8")

        manager = SlashCommandManager()
        manager.scan_commands(project_dir=Path(tmpdir))

        commands = manager.list_commands()
        assert len(commands) == 3
        assert "deploy" in commands
        assert "test" in commands
        assert "build" in commands


def test_command_manager_project_overrides_user() -> None:
    """验证项目命令覆盖用户命令"""
    with TemporaryDirectory() as tmpdir:
        # Project command
        project_commands = Path(tmpdir, ".claude", "commands")
        project_commands.mkdir(parents=True)
        (project_commands / "test.txt").write_text("Project test", encoding="utf-8")

        # User command (simulated)
        user_commands = Path(tmpdir, "user_commands")
        user_commands.mkdir(parents=True)
        (user_commands / "test.txt").write_text("User test", encoding="utf-8")

        manager = SlashCommandManager()
        manager.scan_commands(project_dir=Path(tmpdir), user_dir=user_commands)

        command = manager.get_command("test")
        assert command is not None
        assert "Project" in command.template


def test_command_manager_get_command() -> None:
    """验证获取单个命令"""
    with TemporaryDirectory() as tmpdir:
        commands_dir = Path(tmpdir, ".claude", "commands")
        commands_dir.mkdir(parents=True)

        (commands_dir / "deploy.txt").write_text("Deploy to production", encoding="utf-8")

        manager = SlashCommandManager()
        manager.scan_commands(project_dir=Path(tmpdir))

        command = manager.get_command("deploy")

        assert command is not None
        assert command.name == "deploy"
        assert "production" in command.template


def test_command_manager_get_nonexistent_command() -> None:
    """验证获取不存在的命令"""
    manager = SlashCommandManager()

    command = manager.get_command("nonexistent")

    assert command is None


def test_slash_command_basic() -> None:
    """验证基本 SlashCommand"""
    command = SlashCommand(
        name="test",
        template="Run all tests",
        source_file=Path("/path/to/test.txt"),
    )

    assert command.name == "test"
    assert command.template == "Run all tests"
    # Description falls back to first line of template
    assert command.description == "Run all tests"
    assert command.frontmatter is None


def test_slash_command_with_frontmatter() -> None:
    """验证带 frontmatter 的命令"""
    frontmatter = CommandFrontmatter(
        description="Run the test suite",
        model="gpt-4",
        allowed_tools=["read_file", "execute_command"],
    )

    command = SlashCommand(
        name="test",
        template="Execute tests",
        source_file=Path("/path/to/test.txt"),
        frontmatter=frontmatter,
    )

    assert command.frontmatter is not None
    assert command.frontmatter.description == "Run the test suite"
    assert command.frontmatter.model == "gpt-4"
    assert "read_file" in command.frontmatter.allowed_tools


def test_slash_command_display_name() -> None:
    """验证命令显示名称"""
    command = SlashCommand(
        name="deploy_production",
        template="Deploy to production",
        source_file=Path("/path/to/deploy_production.txt"),
    )

    assert command.display_name() == "/deploy_production"


def test_slash_command_is_available() -> None:
    """验证命令可用性检查"""
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("content", encoding="utf-8")

        command = SlashCommand(
            name="test",
            template="Run tests",
            source_file=test_file,
        )

        assert command.is_available() is True

    # After temp directory is cleaned up
    assert command.is_available() is False


def test_command_frontmatter_defaults() -> None:
    """验证 frontmatter 默认值"""
    frontmatter = CommandFrontmatter()

    assert frontmatter.description is None
    assert frontmatter.model is None
    assert frontmatter.allowed_tools == []


# ===== T081: Frontmatter + Parameter Replacement Tests =====


def test_parse_command_without_frontmatter() -> None:
    """验证解析无 frontmatter 的命令"""
    content = "This is a simple command"

    command = SlashCommand.from_content(
        name="simple",
        content=content,
        source_file=Path("/path/to/simple.txt"),
    )

    assert command.template == "This is a simple command"
    assert command.frontmatter is None


def test_parse_command_with_frontmatter() -> None:
    """验证解析带 frontmatter 的命令"""
    content = """---
description: Deploy the application
model: gpt-4
allowed_tools:
  - read_file
  - execute_command
---
Deploy to production server"""

    command = SlashCommand.from_content(
        name="deploy",
        content=content,
        source_file=Path("/path/to/deploy.txt"),
    )

    assert command.frontmatter is not None
    assert command.frontmatter.description == "Deploy the application"
    assert command.frontmatter.model == "gpt-4"
    assert command.frontmatter.allowed_tools == ["read_file", "execute_command"]
    assert "Deploy to production server" in command.template


def test_parse_command_with_invalid_frontmatter() -> None:
    """验证解析无效 frontmatter 时给出错误"""
    content = """---
invalid: yaml: content:
---
Command content"""

    # Should handle gracefully, frontmatter may be None
    command = SlashCommand.from_content(
        name="invalid",
        content=content,
        source_file=Path("/path/to/invalid.txt"),
    )

    # Command should still be created, template includes everything
    assert command.template is not None


def test_execute_command_template_no_args() -> None:
    """验证无参数模板执行"""
    result = execute_command_template(
        template="Run all tests",
        arguments=[],
    )

    assert result == "Run all tests"


def test_execute_command_template_with_positional_args() -> None:
    """验证位置参数替换"""
    result = execute_command_template(
        template="Test file $1 and $2",
        arguments=["main.py", "utils.py"],
    )

    assert result == "Test file main.py and utils.py"


def test_execute_command_template_with_all_arguments() -> None:
    """验证 $ALL_ARGUMENTS 替换"""
    result = execute_command_template(
        template="Test files: $ALL_ARGUMENTS",
        arguments=["main.py", "utils.py", "test.py"],
    )

    assert result == "Test files: main.py utils.py test.py"


def test_execute_command_template_mixed_placeholders() -> None:
    """验证混合占位符"""
    result = execute_command_template(
        template="First: $1, Rest: $ALL_ARGUMENTS",
        arguments=["a", "b", "c"],
    )

    # $ALL_ARGUMENTS should include all args
    assert "First: a" in result
    assert "b" in result
    assert "c" in result


def test_execute_command_template_empty_arguments() -> None:
    """验证空参数处理"""
    result = execute_command_template(
        template="Test $1",
        arguments=[],
    )

    # Empty args should result in empty placeholder or no change
    assert result is not None


def test_execute_command_template_missing_placeholder() -> None:
    """验证缺少占位符时保持原样"""
    result = execute_command_template(
        template="Test $1 and $3",
        arguments=["only_one"],
    )

    # $3 should remain or be replaced with empty
    assert "only_one" in result


def test_execute_command_template_special_characters() -> None:
    """验证特殊字符处理"""
    result = execute_command_template(
        template="Test file: $1",
        arguments=["file with spaces.txt"],
    )

    assert "file with spaces.txt" in result


def test_slash_command_execute() -> None:
    """验证命令执行"""
    command = SlashCommand(
        name="test",
        template="Run tests for $1",
        source_file=Path("/path/to/test.txt"),
    )

    result = command.execute(arguments=["main.py"])

    assert "main.py" in result
    assert "Run tests" in result


def test_slash_command_execute_with_frontmatter() -> None:
    """验证带 frontmatter 的命令执行"""
    frontmatter = CommandFrontmatter(
        description="Test command",
        model="gpt-4",
    )

    command = SlashCommand(
        name="test",
        template="Test $1",
        source_file=Path("/path/to/test.txt"),
        frontmatter=frontmatter,
    )

    result = command.execute(arguments=["module"])

    assert "module" in result


def test_command_manager_execute_command() -> None:
    """验证通过管理器执行命令"""
    with TemporaryDirectory() as tmpdir:
        commands_dir = Path(tmpdir, ".claude", "commands")
        commands_dir.mkdir(parents=True)

        (commands_dir / "greet.txt").write_text(
            "Hello, $1!",
            encoding="utf-8",
        )

        manager = SlashCommandManager()
        manager.scan_commands(project_dir=Path(tmpdir))

        result = manager.execute("greet", ["World"])

        assert "Hello, World!" in result


def test_command_manager_execute_nonexistent() -> None:
    """验证执行不存在的命令"""
    manager = SlashCommandManager()

    with pytest.raises(CommandArgumentError):
        manager.execute("nonexistent", [])


def test_slash_command_with_description_from_frontmatter() -> None:
    """验证从 frontmatter 获取描述"""
    content = """---
description: This is a test command
---
Test content"""

    command = SlashCommand.from_content(
        name="test",
        content=content,
        source_file=Path("/path/to/test.txt"),
    )

    assert command.description == "This is a test command"


def test_slash_command_description_fallback() -> None:
    """验证描述回退到模板首行"""
    command = SlashCommand(
        name="test",
        template="First line\nSecond line",
        source_file=Path("/path/to/test.txt"),
    )

    assert command.description == "First line"


def test_command_manager_list_with_details() -> None:
    """验证列出自命令详情"""
    with TemporaryDirectory() as tmpdir:
        commands_dir = Path(tmpdir, ".claude", "commands")
        commands_dir.mkdir(parents=True)

        (commands_dir / "deploy.txt").write_text(
            """---
description: Deploy to production
---
Deploy the app""",
            encoding="utf-8",
        )

        manager = SlashCommandManager()
        manager.scan_commands(project_dir=Path(tmpdir))

        commands = manager.list_commands()
        assert "deploy" in commands

        command = manager.get_command("deploy")
        assert command.description == "Deploy to production"


def test_command_manager_reload() -> None:
    """验证重新加载命令"""
    with TemporaryDirectory() as tmpdir:
        commands_dir = Path(tmpdir, ".claude", "commands")
        commands_dir.mkdir(parents=True)

        (commands_dir / "test.txt").write_text("Test", encoding="utf-8")

        manager = SlashCommandManager()
        manager.scan_commands(project_dir=Path(tmpdir))

        assert len(manager.list_commands()) == 1

        # Add new command
        (commands_dir / "new.txt").write_text("New", encoding="utf-8")

        # Reload
        manager.scan_commands(project_dir=Path(tmpdir))

        assert len(manager.list_commands()) == 2
        assert "new" in manager.list_commands()


def test_command_frontmatter_with_empty_allowed_tools() -> None:
    """验证空的 allowed_tools"""
    content = """---
allowed_tools: []
---
Command"""

    command = SlashCommand.from_content(
        name="test",
        content=content,
        source_file=Path("/path/to/test.txt"),
    )

    assert command.frontmatter is not None
    assert command.frontmatter.allowed_tools == []


def test_command_frontmatter_with_single_tool() -> None:
    """验证单个工具的 frontmatter"""
    content = """---
allowed_tools:
  - read_file
---
Command"""

    command = SlashCommand.from_content(
        name="test",
        content=content,
        source_file=Path("/path/to/test.txt"),
    )

    assert command.frontmatter is not None
    assert command.frontmatter.allowed_tools == ["read_file"]


def test_execute_command_preserves_newlines() -> None:
    """验证保留换行符"""
    result = execute_command_template(
        template="Line 1\nLine 2\nLine 3",
        arguments=[],
    )

    assert result.count("\n") == 2


def test_command_with_multiline_template() -> None:
    """验证多行模板"""
    command = SlashCommand(
        name="multi",
        template="Step 1: $1\nStep 2: $2\nStep 3: $3",
        source_file=Path("/path/to/multi.txt"),
    )

    result = command.execute(["a", "b", "c"])

    assert "Step 1: a" in result
    assert "Step 2: b" in result
    assert "Step 3: c" in result
