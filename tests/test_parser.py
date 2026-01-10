"""
Parser tests - @file and !command syntax parsing

TDD: 测试先行
"""

import pytest

from deep_code.interaction.parser import (
    CommandReference,
    DirectoryReference,
    FileReference,
    Parser,
    ParsedInput,
    parse_input,
)


def test_parser_create() -> None:
    """验证创建 Parser"""
    parser = Parser()
    assert parser is not None


def test_parse_plain_text() -> None:
    """验证解析纯文本（无引用）"""
    parser = Parser()
    result = parser.parse("Hello, world!")

    assert result.prompt == "Hello, world!"
    assert not result.has_references()
    assert len(result.file_refs) == 0
    assert len(result.directory_refs) == 0
    assert len(result.command_refs) == 0


def test_parse_file_reference() -> None:
    """验证解析文件引用"""
    parser = Parser()
    result = parser.parse("@README.md")

    assert len(result.file_refs) == 1
    assert result.file_refs[0].path == "README.md"
    assert result.file_refs[0].line_range is None


def test_parse_file_reference_with_line_range() -> None:
    """验证解析文件引用（带行号范围）"""
    parser = Parser()
    result = parser.parse("@main.py:10-20")

    assert len(result.file_refs) == 1
    assert result.file_refs[0].path == "main.py"
    assert result.file_refs[0].line_range == (10, 20)


def test_parse_directory_reference() -> None:
    """验证解析目录引用"""
    parser = Parser()
    result = parser.parse("@src/")

    assert len(result.directory_refs) == 1
    assert result.directory_refs[0].path == "src"
    assert result.directory_refs[0].recursive is True


def test_parse_command_reference() -> None:
    """验证解析命令引用"""
    parser = Parser()
    result = parser.parse("!ls -la")

    assert len(result.command_refs) == 1
    assert result.command_refs[0].command == "ls -la"


def test_parse_mixed_references() -> None:
    """验证解析混合引用"""
    parser = Parser()
    result = parser.parse("Check @README.md and @src/ then run !ls")

    assert len(result.file_refs) == 1
    assert len(result.directory_refs) == 1
    assert len(result.command_refs) == 1
    assert "Check" in result.prompt


def test_parse_multiple_files() -> None:
    """验证解析多个文件引用"""
    parser = Parser()
    result = parser.parse("@file1.py @file2.py @file3.py")

    assert len(result.file_refs) == 3
    assert result.file_refs[0].path == "file1.py"
    assert result.file_refs[1].path == "file2.py"
    assert result.file_refs[2].path == "file3.py"


def test_parse_with_windows_path() -> None:
    """验证解析 Windows 路径（正斜杠版本）"""
    parser = Parser()
    # Use forward slashes (works on all platforms)
    result = parser.parse("@C:/Users/test/file.txt")

    # Forward slash path should work
    assert len(result.file_refs) == 1
    assert "Users" in result.file_refs[0].path


def test_parse_with_relative_path() -> None:
    """验证解析相对路径（不包含 / 结尾）"""
    parser = Parser()
    # Use a simple filename without /
    result = parser.parse("@file.md")

    assert len(result.file_refs) == 1
    assert result.file_refs[0].path == "file.md"


def test_parse_nested_directory() -> None:
    """验证解析嵌套目录"""
    parser = Parser()
    result = parser.parse("@src/cli/")

    assert len(result.directory_refs) == 1
    assert result.directory_refs[0].path == "src/cli"


def test_file_reference_str() -> None:
    """验证 FileReference 字符串表示"""
    ref = FileReference("test.py", (10, 20))
    assert str(ref) == "@test.py:10-20"

    ref2 = FileReference("test.py")
    assert str(ref2) == "@test.py"


def test_directory_reference_str() -> None:
    """验证 DirectoryReference 字符串表示"""
    ref = DirectoryReference("src", recursive=True)
    assert str(ref) == "@src/"


def test_command_reference_str() -> None:
    """验证 CommandReference 字符串表示"""
    ref = CommandReference("ls -la")
    assert str(ref) == "!ls -la"


def test_has_references() -> None:
    """验证 has_references 方法"""
    parser = Parser()

    result1 = parser.parse("plain text")
    assert not result1.has_references()

    result2 = parser.parse("@file.md")
    assert result2.has_references()


def test_get_all_references() -> None:
    """验证获取所有引用"""
    parser = Parser()
    result = parser.parse("@file1.txt @dir/ !ls")

    refs = result.get_all_references()
    assert len(refs) == 3


def test_is_command_only() -> None:
    """验证 is_command_only 方法"""
    parser = Parser()

    assert parser.is_command_only("!ls")
    assert parser.is_command_only("!ls -la")
    # With text before !, it's not command-only
    assert not parser.is_command_only("check !ls")


def test_extract_line_range() -> None:
    """验证提取行号范围"""
    parser = Parser()

    assert parser.extract_line_range("file:10-20") == (10, 20)
    assert parser.extract_line_range("file:1-100") == (1, 100)
    assert parser.extract_line_range("file") is None


def test_convenience_function() -> None:
    """验证便捷函数 parse_input"""
    result = parse_input("@test.txt")

    assert len(result.file_refs) == 1
    assert result.file_refs[0].path == "test.txt"


def test_prompt_without_references() -> None:
    """验证移除引用后的提示文本"""
    parser = Parser()
    result = parser.parse("Please review @README.md for details")

    assert "Please review" in result.prompt
    assert "for details" in result.prompt
    assert "@README.md" not in result.prompt


def test_command_removed_from_prompt() -> None:
    """验证命令从提示中移除"""
    parser = Parser()
    result = parser.parse("Check status !git status")

    assert "Check status" in result.prompt
    assert "!git status" not in result.prompt
