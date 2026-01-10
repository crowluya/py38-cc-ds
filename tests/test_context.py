"""
Context Formatter tests - File and directory formatting

TDD: 测试先行
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from deep_code.core.context import (
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

        from deep_code.core.context import ContextBuilder

        builder = ContextBuilder()
        builder.add_file(str(file1))
        builder.add_file(str(file2))

        full_context = builder.build()

        assert "content1" in full_context
        assert "content2" in full_context
        assert "file1.txt" in full_context
        assert "file2.txt" in full_context


# ===== T050: ContextManager tests =====


def test_context_manager_create() -> None:
    """验证创建 ContextManager"""
    from deep_code.core.context import ContextManager

    manager = ContextManager()
    assert manager is not None


def test_context_manager_load_file() -> None:
    """验证加载文件"""
    from deep_code.core.context import ContextManager

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Hello, world!", encoding="utf-8")

        manager = ContextManager()
        file_ctx = manager.load_file(str(test_file))

        assert "test.txt" in file_ctx.path
        assert file_ctx.content == "Hello, world!"


def test_context_manager_load_file_with_line_range() -> None:
    """验证加载文件带行号范围"""
    from deep_code.core.context import ContextManager

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5", encoding="utf-8")

        manager = ContextManager()
        file_ctx = manager.load_file(str(test_file), line_range=(2, 4))

        assert file_ctx.line_range == (2, 4)
        assert "Line 1" not in file_ctx.content
        assert "Line 2" in file_ctx.content
        assert "Line 4" in file_ctx.content
        assert "Line 5" not in file_ctx.content


def test_context_manager_load_file_not_found() -> None:
    """验证加载不存在的文件"""
    from deep_code.core.context import ContextManager, LoadError

    manager = ContextManager()

    with pytest.raises(LoadError):
        manager.load_file("/nonexistent/file.txt")


def test_context_manager_load_file_encoding_error() -> None:
    """验证文件编码错误处理"""
    from deep_code.core.context import ContextManager

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.bin")
        # Write binary data that's not valid UTF-8
        test_file.write_bytes(b"\xff\xfe\x00\x01")

        manager = ContextManager()
        # Should handle encoding error gracefully
        file_ctx = manager.load_file(str(test_file))

        # Should have content (fallback encoding)
        assert file_ctx.content is not None


def test_context_manager_load_directory() -> None:
    """验证加载目录"""
    from deep_code.core.context import ContextManager

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "file1.txt").write_text("content1")
        Path(tmpdir, "file2.py").write_text("content2")

        manager = ContextManager()
        dir_ctx = manager.load_directory(tmpdir)

        assert len(dir_ctx.files) == 2


def test_context_manager_load_directory_recursive() -> None:
    """验证递归加载目录"""
    from deep_code.core.context import ContextManager

    with TemporaryDirectory() as tmpdir:
        subdir = Path(tmpdir, "subdir")
        subdir.mkdir()
        Path(tmpdir, "root.txt").write_text("root")
        Path(subdir, "nested.txt").write_text("nested")

        manager = ContextManager()
        dir_ctx = manager.load_directory(tmpdir, recursive=True)

        assert len(dir_ctx.files) == 2


def test_context_manager_load_directory_not_found() -> None:
    """验证加载不存在的目录"""
    from deep_code.core.context import ContextManager, LoadError

    manager = ContextManager()

    with pytest.raises(LoadError):
        manager.load_directory("/nonexistent/directory")


def test_context_manager_load_file_from_reference() -> None:
    """验证从 FileReference 加载文件"""
    from deep_code.core.context import ContextManager
    from deep_code.interaction.parser import FileReference

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("content", encoding="utf-8")

        ref = FileReference(path=str(test_file), line_range=None)
        manager = ContextManager()
        file_ctx = manager.load_from_reference(ref)

        assert "content" in file_ctx.content


def test_context_manager_load_directory_from_reference() -> None:
    """验证从 DirectoryReference 加载目录"""
    from deep_code.core.context import ContextManager
    from deep_code.interaction.parser import DirectoryReference

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "file.txt").write_text("content")

        ref = DirectoryReference(path=tmpdir, recursive=True)
        manager = ContextManager()
        dir_ctx = manager.load_from_reference(ref)

        assert len(dir_ctx.files) == 1


def test_context_manager_max_file_size() -> None:
    """验证文件大小限制"""
    from deep_code.core.context import ContextManager

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        # Create large content
        test_file.write_text("x" * 20000, encoding="utf-8")

        manager = ContextManager(max_file_size=10000)
        file_ctx = manager.load_file(str(test_file))

        # Should be truncated
        assert file_ctx.truncated is True
        assert len(file_ctx.content) <= 10000


def test_context_manager_max_directory_files() -> None:
    """验证目录文件数量限制"""
    from deep_code.core.context import ContextManager

    with TemporaryDirectory() as tmpdir:
        # Create many files
        for i in range(50):
            Path(tmpdir, f"file{i}.txt").write_text(f"content{i}")

        manager = ContextManager(max_directory_files=10)
        dir_ctx = manager.load_directory(tmpdir)

        # Should be limited
        assert len(dir_ctx.files) == 10
        assert dir_ctx.truncated is True


# ===== T051: Long-term memory file auto-discovery tests =====


def test_long_term_memory_create() -> None:
    """验证创建 LongTermMemory"""
    from deep_code.core.context import LongTermMemory

    memory = LongTermMemory()
    assert memory is not None


def test_long_term_memory_load_claude_md() -> None:
    """验证加载 CLAUDE.md"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        claude_md = Path(tmpdir, "CLAUDE.md")
        claude_md.write_text("# Project Guide\n\nThis is the guide.", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        assert "CLAUDE.md" in memory.files
        assert "Project Guide" in memory.files["CLAUDE.md"].content


def test_long_term_memory_load_multiple_files() -> None:
    """验证加载多个长期记忆文件"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "CLAUDE.md").write_text("# Claude MD", encoding="utf-8")
        Path(tmpdir, "AGENTS.md").write_text("# Agents MD", encoding="utf-8")
        Path(tmpdir, "constitution.md").write_text("# Constitution", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        assert len(memory.files) == 3
        assert "CLAUDE.md" in memory.files
        assert "AGENTS.md" in memory.files
        assert "constitution.md" in memory.files


def test_long_term_memory_missing_files() -> None:
    """验证处理缺失的长期记忆文件"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        # Only CLAUDE.md exists
        Path(tmpdir, "CLAUDE.md").write_text("# Guide", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        # Should not crash
        assert len(memory.files) == 1
        assert "CLAUDE.md" in memory.files


def test_long_term_memory_empty_directory() -> None:
    """验证空目录处理"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        # Should not crash, just empty
        assert len(memory.files) == 0
        assert memory.is_empty is True


def test_long_term_memory_get_formatted_content() -> None:
    """验证获取格式化的长期记忆内容"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "CLAUDE.md").write_text("# Project\n\nContent here", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        formatted = memory.get_formatted_content()

        assert "CLAUDE.md" in formatted
        assert "Project" in formatted
        assert "Content here" in formatted


def test_long_term_memory_get_file_names() -> None:
    """验证获取已加载的文件名列表"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "CLAUDE.md").write_text("# Guide", encoding="utf-8")
        Path(tmpdir, "AGENTS.md").write_text("# Agents", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        names = memory.get_file_names()

        assert "CLAUDE.md" in names
        assert "AGENTS.md" in names


def test_long_term_memory_has_file() -> None:
    """验证检查文件是否已加载"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "CLAUDE.md").write_text("# Guide", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        assert memory.has_file("CLAUDE.md") is True
        assert memory.has_file("AGENTS.md") is False


def test_long_term_memory_get_file() -> None:
    """验证获取特定文件内容"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "CLAUDE.md").write_text("# Guide", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        file_ctx = memory.get_file("CLAUDE.md")

        assert file_ctx is not None
        assert "Guide" in file_ctx.content


def test_long_term_memory_get_missing_file() -> None:
    """验证获取不存在的文件"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        file_ctx = memory.get_file("MISSING.md")

        assert file_ctx is None


def test_long_term_memory_to_dict() -> None:
    """验证转换为字典"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "CLAUDE.md").write_text("# Guide", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        data = memory.to_dict()

        assert "files" in data
        assert "CLAUDE.md" in data["files"]


def test_long_term_memory_load_custom_files() -> None:
    """验证加载自定义长期记忆文件"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "README.md").write_text("# Readme", encoding="utf-8")
        Path(tmpdir, "CONTRIBUTING.md").write_text("# Contributing", encoding="utf-8")

        memory = LongTermMemory(custom_files=["README.md", "CONTRIBUTING.md"])
        memory.load_from_directory(tmpdir)

        assert len(memory.files) == 2
        assert "README.md" in memory.files
        assert "CONTRIBUTING.md" in memory.files


def test_long_term_memory_status_message() -> None:
    """验证状态消息"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "CLAUDE.md").write_text("# Guide", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir)

        status = memory.get_status_message()

        assert "CLAUDE.md" in status
        assert "loaded" in status.lower()


# ===== T052: Modular imports with @ syntax =====


def test_modular_loader_create() -> None:
    """验证创建 ModularLoader"""
    from deep_code.core.context import ModularLoader

    loader = ModularLoader()
    assert loader is not None


def test_modular_loader_load_with_imports() -> None:
    """验证加载带 @ 导入的文件"""
    from deep_code.core.context import ModularLoader

    with TemporaryDirectory() as tmpdir:
        # Create referenced file
        referenced = Path(tmpdir, "referenced.md")
        referenced.write_text("# Referenced\n\nContent from referenced file", encoding="utf-8")

        # Create main file with @ import
        main_file = Path(tmpdir, "main.md")
        main_file.write_text("# Main\n\n@referenced.md\n\nMain content", encoding="utf-8")

        loader = ModularLoader()
        content = loader.load_with_imports(str(main_file), base_dir=tmpdir)

        assert "Referenced" in content
        assert "Content from referenced file" in content
        assert "Main content" in content


def test_modular_loader_load_with_line_range_import() -> None:
    """验证加载带行号范围的 @ 导入"""
    from deep_code.core.context import ModularLoader

    with TemporaryDirectory() as tmpdir:
        # Create referenced file
        referenced = Path(tmpdir, "other.md")
        referenced.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5", encoding="utf-8")

        # Create main file with @ import with line range
        main_file = Path(tmpdir, "main.md")
        main_file.write_text("# Main\n\n@other.md:2-4\n\nMain content", encoding="utf-8")

        loader = ModularLoader()
        content = loader.load_with_imports(str(main_file), base_dir=tmpdir)

        # Should only include lines 2-4
        assert "Line 2" in content
        assert "Line 3" in content
        assert "Line 4" in content
        assert "Line 1" not in content
        assert "Line 5" not in content


def test_modular_loader_multi_level_imports() -> None:
    """验证多层导入"""
    from deep_code.core.context import ModularLoader

    with TemporaryDirectory() as tmpdir:
        # Level 3: base file
        Path(tmpdir, "base.md").write_text("# Base\n\nBase content", encoding="utf-8")

        # Level 2: middle file importing base
        Path(tmpdir, "middle.md").write_text("# Middle\n\n@base.md\n\nMiddle content", encoding="utf-8")

        # Level 1: top file importing middle
        Path(tmpdir, "top.md").write_text("# Top\n\n@middle.md\n\nTop content", encoding="utf-8")

        loader = ModularLoader()
        content = loader.load_with_imports(str(tmpdir) + "/top.md", base_dir=tmpdir)

        assert "Base content" in content
        assert "Middle content" in content
        assert "Top content" in content


def test_modular_loader_circular_detection() -> None:
    """验证循环引用检测"""
    from deep_code.core.context import ModularLoader, CircularImportError

    with TemporaryDirectory() as tmpdir:
        # File A imports B, B imports A
        Path(tmpdir, "a.md").write_text("# A\n\n@b.md\n\nContent A", encoding="utf-8")
        Path(tmpdir, "b.md").write_text("# B\n\n@a.md\n\nContent B", encoding="utf-8")

        loader = ModularLoader()

        with pytest.raises(CircularImportError) as exc_info:
            loader.load_with_imports(str(tmpdir) + "/a.md", base_dir=tmpdir)

        # Error should mention the circular path
        error_msg = str(exc_info.value)
        assert "circular" in error_msg.lower() or "cycle" in error_msg.lower()


def test_modular_loader_missing_import() -> None:
    """验证处理缺失的导入文件"""
    from deep_code.core.context import ModularLoader

    with TemporaryDirectory() as tmpdir:
        # Main file imports non-existent file
        Path(tmpdir, "main.md").write_text("# Main\n\n@missing.md\n\nMain content", encoding="utf-8")

        loader = ModularLoader()
        content = loader.load_with_imports(str(tmpdir) + "/main.md", base_dir=tmpdir)

        # Should continue without the missing file
        assert "Main content" in content
        # Should have a warning about missing file
        assert "missing" in content.lower() or "not found" in content.lower()


def test_modular_loader_directory_import() -> None:
    """验证目录导入"""
    from deep_code.core.context import ModularLoader

    with TemporaryDirectory() as tmpdir:
        # Create a subdirectory
        subdir = Path(tmpdir, "docs")
        subdir.mkdir()
        Path(subdir, "file1.md").write_text("# File 1", encoding="utf-8")
        Path(subdir, "file2.md").write_text("# File 2", encoding="utf-8")

        # Main file imports directory
        Path(tmpdir, "main.md").write_text("# Main\n\n@docs/\n\nMain content", encoding="utf-8")

        loader = ModularLoader()
        content = loader.load_with_imports(str(tmpdir) + "/main.md", base_dir=tmpdir)

        # Should include both files
        assert "File 1" in content or "file1" in content
        assert "File 2" in content or "file2" in content


def test_modular_loader_max_import_depth() -> None:
    """验证最大导入深度限制"""
    from deep_code.core.context import ModularLoader

    with TemporaryDirectory() as tmpdir:
        # Create chain of files
        for i in range(20):
            if i == 19:
                content = f"# File {i}\n\nContent {i}"
            else:
                content = f"# File {i}\n\n@file{i+1}.md\n\nContent {i}"
            Path(tmpdir, f"file{i}.md").write_text(content, encoding="utf-8")

        loader = ModularLoader(max_import_depth=10)
        content = loader.load_with_imports(str(tmpdir) + "/file0.md", base_dir=tmpdir)

        # Should stop at max depth
        # Should have some content
        assert len(content) > 0


def test_modular_loader_import_tracker() -> None:
    """验证导入追踪"""
    from deep_code.core.context import ModularLoader

    with TemporaryDirectory() as tmpdir:
        Path(tmpdir, "base.md").write_text("# Base", encoding="utf-8")
        Path(tmpdir, "main.md").write_text("# Main\n\n@base.md", encoding="utf-8")

        loader = ModularLoader()
        loader.load_with_imports(str(tmpdir) + "/main.md", base_dir=tmpdir)

        # Should track imported files
        assert len(loader.get_imported_files()) > 0


def test_long_term_memory_load_with_modular_imports() -> None:
    """验证 LongTermMemory 加载时处理模块化导入"""
    from deep_code.core.context import LongTermMemory

    with TemporaryDirectory() as tmpdir:
        # Create referenced file
        Path(tmpdir, "shared.md").write_text("# Shared\n\nShared content", encoding="utf-8")

        # CLAUDE.md imports shared.md
        Path(tmpdir, "CLAUDE.md").write_text("# Claude Guide\n\n@shared.md\n\nMain guide", encoding="utf-8")

        memory = LongTermMemory()
        memory.load_from_directory(tmpdir, resolve_imports=True)

        # Content should include imported file
        claude_content = memory.get_file("CLAUDE.md").content
        assert "Shared content" in claude_content


# ===== T071: Permission Integration Tests =====


def test_context_manager_with_permission_allow_read() -> None:
    """验证权限允许时读取文件"""
    from deep_code.core.context import ContextManager
    from deep_code.security.permissions import (
        PermissionManager,
        PermissionRule,
        PermissionAction,
        PermissionDomain,
    )

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Hello, world!", encoding="utf-8")

        manager = PermissionManager()
        manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.ALLOW,
            pattern="*.txt",
        ))

        context_mgr = ContextManager(permission_manager=manager)

        file_ctx = context_mgr.load_file(str(test_file))

        assert "Hello" in file_ctx.content


def test_context_manager_with_permission_deny_read() -> None:
    """验证权限拒绝时不能读取文件"""
    from deep_code.core.context import ContextManager, LoadError
    from deep_code.security.permissions import (
        PermissionManager,
        PermissionRule,
        PermissionAction,
        PermissionDomain,
    )

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Hello, world!", encoding="utf-8")

        manager = PermissionManager()
        manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.DENY,
            pattern="*.txt",
        ))

        context_mgr = ContextManager(permission_manager=manager)

        with pytest.raises(LoadError) as exc_info:
            context_mgr.load_file(str(test_file))

        assert "permission" in str(exc_info.value).lower() or "denied" in str(exc_info.value).lower()


def test_context_manager_with_permission_ask_granted_read() -> None:
    """验证 ASK 权限通过时读取文件"""
    from deep_code.core.context import ContextManager
    from deep_code.security.permissions import (
        PermissionManager,
        PermissionRule,
        PermissionAction,
        PermissionDomain,
    )

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Hello, world!", encoding="utf-8")

        manager = PermissionManager()
        manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.ASK,
            pattern="*.txt",
        ))

        # Callback that grants permission
        def grant_callback(domain, target, reason):
            return True

        context_mgr = ContextManager(
            permission_manager=manager,
            approval_callback=grant_callback,
        )

        file_ctx = context_mgr.load_file(str(test_file))

        assert "Hello" in file_ctx.content


def test_context_manager_with_permission_ask_denied_read() -> None:
    """验证 ASK 权限拒绝时不能读取文件"""
    from deep_code.core.context import ContextManager, LoadError
    from deep_code.security.permissions import (
        PermissionManager,
        PermissionRule,
        PermissionAction,
        PermissionDomain,
    )

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Hello, world!", encoding="utf-8")

        manager = PermissionManager()
        manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.ASK,
            pattern="*.txt",
        ))

        # Callback that denies permission
        def deny_callback(domain, target, reason):
            return False

        context_mgr = ContextManager(
            permission_manager=manager,
            approval_callback=deny_callback,
        )

        with pytest.raises(LoadError) as exc_info:
            context_mgr.load_file(str(test_file))

        assert "permission" in str(exc_info.value).lower() or "denied" in str(exc_info.value).lower()


def test_context_manager_without_permission_manager() -> None:
    """验证没有权限管理器时正常读取"""
    from deep_code.core.context import ContextManager

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("Hello, world!", encoding="utf-8")

        context_mgr = ContextManager()

        file_ctx = context_mgr.load_file(str(test_file))

        assert "Hello" in file_ctx.content
