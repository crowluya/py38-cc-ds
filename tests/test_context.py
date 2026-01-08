"""
Context Formatter tests - File and directory formatting

TDD: 测试先行
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from claude_code.core.context import (
    ContextFormatter,
    FileContext,
    DirectoryContext,
    format_file_context,
    format_directory_context,
)


def test_formatter_create() -> None:
    """验证创建 ContextFormatter"""
    formatter = ContextFormatter()
    assert formatter is not None


def test_format_file_basic() -> None:
    """验证基本文件格式化"""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Hello, world!", encoding="utf-8")

        formatter = ContextFormatter()
        context = formatter.format_file(str(test_file))

        assert "test.txt" in context.path
        assert context.content == "Hello, world!"
        assert "test.txt" in str(context)


def test_format_file_with_line_range() -> None:
    """验证带行号范围的文件格式化"""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5", encoding="utf-8")

        formatter = ContextFormatter()
        context = formatter.format_file(str(test_file), line_range=(2, 4))

        assert context.line_range == (2, 4)
        # Should only include lines 2-4
        assert "Line 1" not in context.content
        assert "Line 2" in context.content
        assert "Line 3" in context.content
        assert "Line 4" in context.content
        assert "Line 5" not in context.content


def test_format_file_truncation() -> None:
    """验证超长内容截断"""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        # Create content larger than default max size
        content = "Line " * 1000
        test_file.write_text(content, encoding="utf-8")

        formatter = ContextFormatter(max_content_length=500)
        context = formatter.format_file(str(test_file))

        # Content should be truncated
        assert len(context.content) <= 500
        assert context.truncated is True


def test_format_file_no_truncation() -> None:
    """验证内容未超长时不截断"""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        content = "Short content"
        test_file.write_text(content, encoding="utf-8")

        formatter = ContextFormatter(max_content_length=1000)
        context = formatter.format_file(str(test_file))

        assert context.content == content
        assert context.truncated is False


def test_format_file_with_line_numbers() -> None:
    """验证带行号显示的格式化"""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")

        formatter = ContextFormatter()
        context = formatter.format_file(str(test_file))

        # Should include line numbers in formatted output when requested
        formatted = context.format(show_line_numbers=True)
        assert "1:" in formatted
        assert "2:" in formatted
        assert "3:" in formatted


def test_format_file_nonexistent() -> None:
    """验证不存在文件的处理"""
    formatter = ContextFormatter()

    with pytest.raises(FileNotFoundError):
        formatter.format_file("/nonexistent/file.txt")


def test_format_directory_basic() -> None:
    """验证基本目录格式化"""
    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "file1.txt").write_text("content1")
        Path(tmpdir, "file2.py").write_text("content2")
        subdir = Path(tmpdir, "subdir")
        subdir.mkdir()
        Path(subdir, "nested.txt").write_text("nested")

        formatter = ContextFormatter()
        context = formatter.format_directory(tmpdir, recursive=True)

        assert len(context.files) == 3  # All files
        assert context.truncated is False


def test_format_directory_with_gitignore() -> None:
    """验证目录格式化时应用 gitignore"""
    with TemporaryDirectory() as tmpdir:
        # Create .gitignore
        Path(tmpdir, ".gitignore").write_text("*.log\n")

        # Create files
        Path(tmpdir, "test.txt").write_text("text")
        Path(tmpdir, "test.log").write_text("log")

        formatter = ContextFormatter()
        context = formatter.format_directory(tmpdir, recursive=True)

        # Only .txt file should be included
        assert len(context.files) == 1
        assert "test.txt" in context.files[0].path
        assert "test.log" not in str(context.files)


def test_format_directory_max_files() -> None:
    """验证目录文件数量限制"""
    with TemporaryDirectory() as tmpdir:
        # Create many files
        for i in range(20):
            Path(tmpdir, f"file{i}.txt").write_text(f"content{i}")

        formatter = ContextFormatter(max_directory_files=10)
        context = formatter.format_directory(tmpdir, recursive=False)

        # Should only include first 10 files
        assert len(context.files) == 10
        assert context.truncated is True


def test_file_context_str() -> None:
    """验证 FileContext 字符串表示"""
    context = FileContext(
        path="/path/to/file.txt",
        content="Hello",
        line_range=(1, 10),
        truncated=False,
    )

    s = str(context)
    assert "file.txt" in s
    assert "1-10" in s


def test_file_context_format_with_line_numbers() -> None:
    """验证 FileContext format 方法"""
    context = FileContext(
        path="/path/to/file.txt",
        content="Line 1\nLine 2\nLine 3",
        line_range=None,
        truncated=False,
    )

    formatted = context.format(show_line_numbers=True)
    assert "1:" in formatted
    assert "Line 1" in formatted


def test_directory_context_format() -> None:
    """验证 DirectoryContext format 方法"""
    file_ctx1 = FileContext(
        path="/dir/file1.txt",
        content="content1",
        line_range=None,
        truncated=False,
    )
    file_ctx2 = FileContext(
        path="/dir/file2.py",
        content="content2",
        line_range=None,
        truncated=False,
    )

    dir_ctx = DirectoryContext(
        path="/dir",
        files=[file_ctx1, file_ctx2],
        truncated=False,
    )

    formatted = dir_ctx.format()
    assert "file1.txt" in formatted
    assert "file2.py" in formatted


def test_convenience_function_format_file() -> None:
    """验证便捷函数 format_file_context"""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Hello, world!", encoding="utf-8")

        context = format_file_context(str(test_file))

        assert "Hello" in context.content
        assert "test.txt" in context.path


def test_convenience_function_format_directory() -> None:
    """验证便捷函数 format_directory_context"""
    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "file.txt").write_text("content")

        context = format_directory_context(tmpdir)

        assert len(context.files) == 1


def test_format_empty_directory() -> None:
    """验证空目录格式化"""
    with TemporaryDirectory() as tmpdir:
        formatter = ContextFormatter()
        context = formatter.format_directory(tmpdir)

        assert len(context.files) == 0
        assert "Empty directory" in context.format()


def test_truncation_indicator() -> None:
    """验证截断指示器"""
    context = FileContext(
        path="/path/to/file.txt",
        content="Truncated content...",
        truncated=True,
    )

    formatted = context.format()
    assert "(truncated)" in formatted.lower() or "..." in formatted


def test_context_builder() -> None:
    """验证 ContextBuilder 聚合多个上下文"""
    with TemporaryDirectory() as tmpdir:
        file1 = Path(tmpdir, "file1.txt")
        file1.write_text("content1")
        file2 = Path(tmpdir, "file2.txt")
        file2.write_text("content2")

        from claude_code.core.context import ContextBuilder

        builder = ContextBuilder()
        builder.add_file(str(file1))
        builder.add_file(str(file2))

        full_context = builder.build()

        assert "content1" in full_context
        assert "content2" in full_context
        assert "file1.txt" in full_context
        assert "file2.txt" in full_context
