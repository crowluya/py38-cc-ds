"""
Directory Loader tests - Git-aware directory scanning

TDD: 测试先行
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

import pytest

from deep_code.interaction.directory_loader import DirectoryLoader, DirectoryEntry


def test_loader_create() -> None:
    """验证创建 DirectoryLoader"""
    loader = DirectoryLoader()
    assert loader is not None


def test_list_directory_simple() -> None:
    """验证简单目录列表"""
    with TemporaryDirectory() as tmpdir:
        # Create some files
        Path(tmpdir, "file1.txt").write_text("content1")
        Path(tmpdir, "file2.py").write_text("content2")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir)

        assert len(entries) == 2
        paths = [e.path for e in entries]
        assert any("file1.txt" in p for p in paths)
        assert any("file2.py" in p for p in paths)


def test_list_directory_recursive() -> None:
    """验证递归目录列表"""
    with TemporaryDirectory() as tmpdir:
        # Create nested structure
        subdir = Path(tmpdir, "subdir")
        subdir.mkdir()
        Path(tmpdir, "root.txt").write_text("root")
        Path(subdir, "nested.txt").write_text("nested")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir, recursive=True)

        assert len(entries) == 2
        paths = [e.path for e in entries]
        assert any("root.txt" in p for p in paths)
        assert any("nested.txt" in p for p in paths)


def test_filter_git_directory() -> None:
    """验证过滤 .git 目录"""
    with TemporaryDirectory() as tmpdir:
        # Create .git directory
        git_dir = Path(tmpdir, ".git")
        git_dir.mkdir()
        Path(git_dir, "config").write_text("git config")

        # Create normal file
        Path(tmpdir, "normal.txt").write_text("normal")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir)

        assert len(entries) == 1
        assert ".git" not in entries[0].path
        assert "normal.txt" in entries[0].path


def test_filter_common_noise_directories() -> None:
    """验证过滤常见噪音目录"""
    with TemporaryDirectory() as tmpdir:
        # Create noise directories
        for noise in ["node_modules", "__pycache__", ".venv", "venv", "dist", "build"]:
            d = Path(tmpdir, noise)
            d.mkdir()
            Path(d, "file.txt").write_text("noise")

        # Create normal file
        Path(tmpdir, "normal.txt").write_text("normal")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir, recursive=True)

        # Only normal file should remain
        assert len(entries) == 1
        assert "normal.txt" in entries[0].path


def test_filter_pycache() -> None:
    """验证过滤 __pycache__ 目录（包括嵌套）"""
    with TemporaryDirectory() as tmpdir:
        # Create nested __pycache__
        subdir = Path(tmpdir, "src")
        subdir.mkdir()
        pycache = Path(subdir, "__pycache__")
        pycache.mkdir()
        Path(pycache, "module.pyc").write_text("compiled")

        # Create normal file in src
        Path(subdir, "module.py").write_text("source")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir, recursive=True)

        # Only module.py should be included
        assert len(entries) == 1
        assert "module.py" in entries[0].path
        assert "__pycache__" not in entries[0].path


def test_gitignore_patterns() -> None:
    """验证 .gitignore 模式匹配"""
    with TemporaryDirectory() as tmpdir:
        # Create .gitignore
        Path(tmpdir, ".gitignore").write_text("*.log\n*.tmp\ntemp/")

        # Create files matching patterns
        Path(tmpdir, "test.log").write_text("log")
        Path(tmpdir, "file.tmp").write_text("tmp")

        # Create temp directory
        temp_dir = Path(tmpdir, "temp")
        temp_dir.mkdir()
        Path(temp_dir, "inside.txt").write_text("temp file")

        # Create normal file
        Path(tmpdir, "normal.txt").write_text("normal")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir, recursive=True)

        # Only normal.txt should remain
        assert len(entries) == 1
        assert "normal.txt" in entries[0].path


def test_gitignore_negation() -> None:
    """验证 .gitignore 否定模式"""
    with TemporaryDirectory() as tmpdir:
        # Create .gitignore with negation
        Path(tmpdir, ".gitignore").write_text("*.log\n!important.log")

        # Create files
        Path(tmpdir, "debug.log").write_text("debug")
        Path(tmpdir, "important.log").write_text("important")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir)

        # Only important.log should remain (negated)
        assert len(entries) == 1
        assert "important.log" in entries[0].path


def test_gitignore_directory_patterns() -> None:
    """验证 .gitignore 目录模式"""
    with TemporaryDirectory() as tmpdir:
        # Create .gitignore
        Path(tmpdir, ".gitignore").write_text("output/\n*.txt")

        # Create directory with slash (directory only)
        output_dir = Path(tmpdir, "output")
        output_dir.mkdir()
        Path(output_dir, "file.txt").write_text("output file")

        # Create normal txt file (should be filtered by *.txt)
        Path(tmpdir, "normal.txt").write_text("normal")

        # Create normal file (not filtered)
        Path(tmpdir, "normal.py").write_text("python file")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir, recursive=True)

        # output/ directory and *.txt files should be filtered
        # Only normal.py should remain
        assert len(entries) == 1
        assert "normal.py" in entries[0].path


def test_gitignore_wildcard_patterns() -> None:
    """验证 .gitignore 通配符模式"""
    with TemporaryDirectory() as tmpdir:
        # Create .gitignore
        Path(tmpdir, ".gitignore").write_text("*.py[cod]\n*.so\n test?.txt")

        # Create files
        Path(tmpdir, "module.pyc").write_text("compiled")
        Path(tmpdir, "module.pyo").write_text("optimized")
        Path(tmpdir, "library.so").write_text("shared")
        Path(tmpdir, "test1.txt").write_text("test")
        Path(tmpdir, "test2.txt").write_text("test")

        # Create normal file
        Path(tmpdir, "module.py").write_text("source")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir)

        # Only module.py should remain
        assert len(entries) == 1
        assert "module.py" in entries[0].path


def test_gitignore_nested() -> None:
    """验证嵌套 .gitignore 文件"""
    with TemporaryDirectory() as tmpdir:
        # Create root .gitignore
        Path(tmpdir, ".gitignore").write_text("*.log")

        # Create subdirectory with its own .gitignore
        subdir = Path(tmpdir, "subdir")
        subdir.mkdir()
        Path(subdir, ".gitignore").write_text("*.tmp\n!keep.tmp")

        # Create files
        Path(tmpdir, "root.log").write_text("log")
        Path(subdir, "file.tmp").write_text("temp")
        Path(subdir, "keep.tmp").write_text("keep")
        Path(subdir, "normal.txt").write_text("normal")

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir, recursive=True)

        # root.log filtered, file.tmp filtered, keep.tmp negated
        assert len(entries) == 2
        paths = [e.path for e in entries]
        assert any("keep.tmp" in p for p in paths)
        assert any("normal.txt" in p for p in paths)


def test_directory_entry_type() -> None:
    """验证 DirectoryEntry 类型"""
    with TemporaryDirectory() as tmpdir:
        # Create file and directory
        Path(tmpdir, "file.txt").write_text("content")
        Path(tmpdir, "directory").mkdir()

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir)

        file_entry = next(e for e in entries if "file.txt" in e.path)
        dir_entry = next(e for e in entries if "directory" in e.path)

        assert file_entry.is_file
        assert not file_entry.is_directory

        assert dir_entry.is_directory
        assert not dir_entry.is_file


def test_directory_entry_size() -> None:
    """验证 DirectoryEntry 文件大小"""
    with TemporaryDirectory() as tmpdir:
        content = "hello world"  # 11 bytes
        Path(tmpdir, "file.txt").write_text(content)

        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir)

        assert entries[0].size == len(content)


def test_empty_directory() -> None:
    """验证空目录处理"""
    with TemporaryDirectory() as tmpdir:
        loader = DirectoryLoader()
        entries = loader.list_directory(tmpdir)

        assert len(entries) == 0


def test_nonexistent_directory() -> None:
    """验证不存在目录的处理"""
    loader = DirectoryLoader()

    with pytest.raises(FileNotFoundError):
        loader.list_directory("/nonexistent/path/that/does/not/exist")


def test_get_directory_tree() -> None:
    """验证获取目录树结构"""
    with TemporaryDirectory() as tmpdir:
        # Create tree structure
        src = Path(tmpdir, "src")
        src.mkdir()
        tests = Path(tmpdir, "tests")
        tests.mkdir()

        Path(src, "main.py").write_text("main")
        Path(src, "utils.py").write_text("utils")
        Path(tests, "test_main.py").write_text("test")

        loader = DirectoryLoader()
        tree = loader.get_directory_tree(tmpdir)

        # Check tree structure
        assert "src" in tree
        assert "tests" in tree
        assert "main.py" in tree["src"]
        assert "utils.py" in tree["src"]
        assert "test_main.py" in tree["tests"]


def test_get_directory_tree_with_filters() -> None:
    """验证带过滤的目录树"""
    with TemporaryDirectory() as tmpdir:
        # Create structure with noise
        Path(tmpdir, ".git").mkdir()
        Path(tmpdir, ".git", "config").write_text("config")
        Path(tmpdir, "node_modules").mkdir()
        Path(tmpdir, "node_modules", "package").mkdir()

        Path(tmpdir, "src").mkdir()
        Path(tmpdir, "src", "main.py").write_text("main")

        loader = DirectoryLoader()
        tree = loader.get_directory_tree(tmpdir)

        # Noise directories should not appear
        assert ".git" not in tree
        assert "node_modules" not in tree
        assert "src" in tree
        assert "main.py" in tree["src"]
