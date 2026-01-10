"""
Smoke tests - 验证项目基础可运行性

这些测试确保项目骨架可用，作为 TDD 起始点。
"""

import sys
from typing import Any


def test_python_version() -> None:
    """验证 Python 版本兼容性（目标 3.8.10）"""
    # 断言 Python 主版本为 3
    assert sys.version_info.major == 3, f"需要 Python 3.x, 当前 {sys.version}"
    # 断言 Python 次版本至少为 8
    assert sys.version_info.minor >= 8, f"需要 Python 3.8+, 当前 {sys.version}"


def test_package_importable() -> None:
    """验证 deep_code 包可导入"""
    import deep_code  # noqa: F401

    assert deep_code.__name__ == "deep_code"


def test_submodules_exist() -> None:
    """验证核心子模块存在"""
    import deep_code

    expected_submodules = [
        "core",
        "interaction",
        "security",
        "extensions",
        "llm",
        "config",
        "cli",
    ]

    for submodule in expected_submodules:
        # 尝试导入子模块
        module_path = f"deep_code.{submodule}"
        __import__(module_path)
        assert hasattr(deep_code, submodule), f"子模块 {submodule} 不存在"


def test_tests_importable() -> None:
    """验证 tests 包可导入"""
    import tests  # noqa: F401

    assert tests.__name__ == "tests"
