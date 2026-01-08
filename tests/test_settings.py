"""
Settings tests - Data structure with default values

TDD: 测试先行
"""

from typing import Any, Dict

import pytest

from claude_code.config.settings import (
    HookSettings,
    LLMSettings,
    PermissionSettings,
    Settings,
    get_default_settings,
)


def test_llm_settings_defaults() -> None:
    """验证 LLM 设置默认值"""
    llm = LLMSettings()

    assert llm.provider == "openai"
    assert llm.api_key is None
    assert llm.api_base is None
    assert llm.model == "gpt-3.5-turbo"
    assert llm.temperature == 0.7
    assert llm.max_tokens == 2048
    assert llm.timeout == 30
    assert llm.verify_ssl is True
    assert llm.ca_cert is None


def test_llm_settings_custom() -> None:
    """验证 LLM 设置自定义值"""
    llm = LLMSettings(
        provider="requests",
        api_key="test-key",
        api_base="http://localhost:8000",
        model="deepseek-chat",
        temperature=0.5,
        max_tokens=4096,
    )

    assert llm.provider == "requests"
    assert llm.api_key == "test-key"
    assert llm.api_base == "http://localhost:8000"
    assert llm.model == "deepseek-chat"
    assert llm.temperature == 0.5
    assert llm.max_tokens == 4096


def test_permission_settings_defaults() -> None:
    """验证权限设置默认值"""
    perm = PermissionSettings()

    assert perm.default_mode == "ask"
    assert perm.file_read == []
    assert perm.file_write == []
    assert perm.command_execute == []
    assert perm.network_access == []


def test_permission_settings_custom() -> None:
    """验证权限设置自定义值"""
    perm = PermissionSettings(
        default_mode="allow",
        file_read=["*.txt", "*.md"],
        file_write=["*.txt"],
        command_execute=["ls", "cat"],
    )

    assert perm.default_mode == "allow"
    assert "*.txt" in perm.file_read
    assert "*.txt" in perm.file_write
    assert "ls" in perm.command_execute


def test_hook_settings_defaults() -> None:
    """验证 Hook 设置默认值"""
    hooks = HookSettings()

    assert hooks.session_start == []
    assert hooks.pre_tool_use == []
    assert hooks.post_tool_use == []


def test_hook_settings_custom() -> None:
    """验证 Hook 设置自定义值"""
    hooks = HookSettings(
        session_start=["echo 'started'"],
        pre_tool_use=["echo 'before tool'"],
        post_tool_use=["echo 'after tool'"],
    )

    assert "echo 'started'" in hooks.session_start
    assert "echo 'before tool'" in hooks.pre_tool_use
    assert "echo 'after tool'" in hooks.post_tool_use


def test_settings_defaults() -> None:
    """验证 Settings 默认值"""
    settings = Settings()

    assert settings.use_color is True
    assert settings.show_thinking is False
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.project_root is None
    assert settings.checkpoint_dir is None

    # Verify nested defaults
    assert settings.llm.provider == "openai"
    assert settings.permissions.default_mode == "ask"
    assert settings.hooks.session_start == []


def test_settings_to_dict() -> None:
    """验证 Settings 转换为字典"""
    settings = Settings(
        llm=LLMSettings(model="gpt-4"),
        permissions=PermissionSettings(default_mode="allow"),
    )

    result = settings.to_dict()

    assert result["llm"]["model"] == "gpt-4"
    assert result["permissions"]["default_mode"] == "allow"
    assert result["use_color"] is True


def test_settings_from_dict() -> None:
    """验证从字典创建 Settings"""
    data: Dict[str, Any] = {
        "llm": {
            "provider": "requests",
            "model": "deepseek-chat",
            "temperature": 0.5,
        },
        "permissions": {
            "default_mode": "deny",
        },
        "debug": True,
        "log_level": "DEBUG",
    }

    settings = Settings.from_dict(data)

    assert settings.llm.provider == "requests"
    assert settings.llm.model == "deepseek-chat"
    assert settings.llm.temperature == 0.5
    assert settings.permissions.default_mode == "deny"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"


def test_settings_from_dict_partial() -> None:
    """验证从部分字典创建 Settings（使用默认值）"""
    data: Dict[str, Any] = {
        "llm": {
            "model": "gpt-4",
        },
    }

    settings = Settings.from_dict(data)

    assert settings.llm.model == "gpt-4"
    # Other values should use defaults
    assert settings.llm.provider == "openai"
    assert settings.use_color is True
    assert settings.permissions.default_mode == "ask"


def test_get_default_settings() -> None:
    """验证获取默认设置"""
    settings = get_default_settings()

    assert isinstance(settings, Settings)
    assert settings.llm.provider == "openai"
    assert settings.permissions.default_mode == "ask"
