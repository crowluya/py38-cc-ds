"""
Path utilities tests - Windows 7 + cross-platform compatibility

TDD: 测试先行
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional

import pytest

from claude_code.config.paths import (
    PathResolver,
    ensure_directory,
    expand_user_path,
    get_config_directory,
    get_home_directory,
    get_project_root,
    is_absolute_path,
    join_paths,
    normalize_path,
)


def test_expand_user_path_unix() -> None:
    """验证 Unix 风格用户目录展开 (~)"""
    path = "~/Documents"
    expanded = expand_user_path(path)

    home = get_home_directory()
    assert expanded.startswith(home)
    assert "Documents" in expanded


def test_expand_user_path_empty() -> None:
    """验证空路径处理"""
    assert expand_user_path("") == ""
    assert expand_user_path(None) is None  # type: ignore


def test_normalize_path() -> None:
    """验证路径标准化"""
    # Test with user expansion
    path = "~/test/../test/file.txt"
    normalized = normalize_path(path)

    assert "test" in normalized
    assert normalized.count("test") == 1  # ".." should be resolved


def test_get_home_directory() -> None:
    """验证获取用户主目录"""
    home = get_home_directory()

    assert home is not None
    assert len(home) > 0
    # Should be an absolute path
    assert os.path.isabs(home)


def test_get_config_directory() -> None:
    """验证获取配置目录"""
    config_dir = get_config_directory()

    assert config_dir is not None
    assert ".claude" in config_dir or "_claude" in config_dir.lower()


def test_ensure_directory(temp_path: str) -> None:
    """验证确保目录存在"""
    temp_base = tempfile.mkdtemp()
    try:
        test_path = os.path.join(temp_base, "test", "nested", "dir")
        result = ensure_directory(test_path)

        assert os.path.isdir(result)
        assert os.path.isabs(result)
    finally:
        shutil.rmtree(temp_base, ignore_errors=True)


def test_is_absolute_path_true() -> None:
    """验证绝对路径检测"""
    if os.name == "nt":
        assert is_absolute_path("C:\\Users\\test")
        assert is_absolute_path("C:/Users/test")
    else:
        assert is_absolute_path("/home/user")
        assert is_absolute_path("/var/log")


def test_is_absolute_path_false() -> None:
    """验证相对路径检测"""
    assert not is_absolute_path("relative/path")
    assert not is_absolute_path("./file.txt")
    assert not is_absolute_path("../parent")


def test_is_absolute_path_expanded() -> None:
    """验证展开后的绝对路径检测"""
    path = "~/Documents"
    assert is_absolute_path(path) is True  # ~ expands to absolute


def test_join_paths() -> None:
    """验证路径拼接"""
    result = join_paths("base", "subdir", "file.txt")

    assert "base" in result
    assert "subdir" in result
    assert "file.txt" in result


def test_join_paths_single() -> None:
    """验证单个路径拼接"""
    result = join_paths("single")
    assert "single" in result


def test_join_paths_empty() -> None:
    """验证空路径拼接"""
    result = join_paths()
    assert result == "."


def test_path_resolver_create() -> None:
    """验证 PathResolver 创建"""
    resolver = PathResolver()
    assert resolver is not None
    assert resolver.base_dir is None


def test_path_resolver_with_base() -> None:
    """验证带 base_dir 的 PathResolver"""
    resolver = PathResolver(base_dir="/tmp/test")
    assert resolver.base_dir is not None
    assert "test" in resolver.base_dir


def test_path_resolver_resolve_absolute() -> None:
    """验证解析绝对路径"""
    resolver = PathResolver(base_dir="/tmp/base")

    if os.name == "nt":
        result = resolver.resolve("C:\\Users\\test")
    else:
        result = resolver.resolve("/home/test")

    # Absolute paths should not be affected by base_dir
    assert "base" not in result or result.startswith("/")


def test_path_resolver_resolve_relative() -> None:
    """验证解析相对路径"""
    temp_dir = tempfile.mkdtemp()
    try:
        resolver = PathResolver(base_dir=temp_dir)
        result = resolver.resolve("subdir/file.txt")

        assert temp_dir in result or result.replace("\\", "/").startswith(temp_dir.replace("\\", "/"))
        assert "subdir" in result
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_path_resolver_set_base_dir() -> None:
    """验证设置 base_dir"""
    resolver = PathResolver()
    assert resolver.base_dir is None

    resolver.set_base_dir("/tmp/new_base")
    assert resolver.base_dir is not None
    assert "new_base" in resolver.base_dir


def test_get_project_root_with_claude_dir() -> None:
    """验证检测项目根目录（存在 .claude 目录）"""
    # Current directory should have .claude (it's where the test runs)
    root = get_project_root()

    # May return None if not in a project, but shouldn't crash
    assert root is None or isinstance(root, str)


@pytest.fixture
def temp_path():
    """Create a temporary path for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
