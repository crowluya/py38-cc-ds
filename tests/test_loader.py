"""
Configuration loader tests - Layered priority loading

TDD: 测试先行
"""

import json
from pathlib import Path
from typing import Any, Dict
import tempfile
import shutil

import pytest

from claude_code.config.loader import ConfigLoader, load_settings


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_loader_create() -> None:
    """验证 ConfigLoader 可创建"""
    loader = ConfigLoader()
    assert loader is not None


def test_loader_create_with_project_root() -> None:
    """验证带 project_root 创建 ConfigLoader"""
    loader = ConfigLoader(project_root="/tmp/test")
    assert loader is not None


def test_load_default_settings(temp_project_dir: str) -> None:
    """验证加载默认设置（无配置文件）"""
    loader = ConfigLoader(project_root=temp_project_dir)
    settings = loader.load()

    # Should have all default values
    assert settings.llm.provider == "openai"
    assert settings.permissions.default_mode == "ask"
    assert settings.use_color is True


def test_load_user_global_config(temp_project_dir: str) -> None:
    """验证加载用户全局配置"""
    # Create user global config
    user_config_dir = Path.home() / ".my-claude"
    user_config_dir.mkdir(exist_ok=True)
    config_path = user_config_dir / "settings.json"

    # Write test config
    config_data = {
        "llm": {"model": "gpt-4"},
        "debug": True,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    try:
        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        assert settings.llm.model == "gpt-4"
        assert settings.debug is True
    finally:
        # Cleanup
        config_path.unlink()


def test_load_project_shared_config(temp_project_dir: str) -> None:
    """验证加载项目共享配置"""
    # Create .my-claude directory and settings.json
    claude_dir = Path(temp_project_dir) / ".my-claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "settings.json"

    config_data = {
        "llm": {"model": "deepseek-chat"},
        "log_level": "DEBUG",
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    loader = ConfigLoader(project_root=temp_project_dir)
    settings = loader.load()

    assert settings.llm.model == "deepseek-chat"
    assert settings.log_level == "DEBUG"


def test_load_project_local_config(temp_project_dir: str) -> None:
    """验证加载项目本地配置（.local.json）"""
    # Create .my-claude directory and settings.local.json
    claude_dir = Path(temp_project_dir) / ".my-claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "settings.local.json"

    config_data = {
        "llm": {"temperature": 0.5},
        "show_thinking": True,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    loader = ConfigLoader(project_root=temp_project_dir)
    settings = loader.load()

    assert settings.llm.temperature == 0.5
    assert settings.show_thinking is True


def test_config_priority_order(temp_project_dir: str) -> None:
    """验证配置优先级顺序"""
    claude_dir = Path(temp_project_dir) / ".my-claude"
    claude_dir.mkdir(parents=True)

    # Create all three config files with conflicting values
    configs = [
        (claude_dir / "settings.json", {"log_level": "INFO"}),
        (claude_dir / "settings.local.json", {"log_level": "DEBUG"}),
    ]

    for path, data in configs:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    # CLI overrides should win
    loader = ConfigLoader(project_root=temp_project_dir)
    settings = loader.load(cli_overrides={"log_level": "ERROR"})

    assert settings.log_level == "ERROR"


def test_config_priority_without_cli(temp_project_dir: str) -> None:
    """验证配置优先级（无 CLI 覆盖）"""
    claude_dir = Path(temp_project_dir) / ".my-claude"
    claude_dir.mkdir(parents=True)

    # settings.local.json should override settings.json
    with open(claude_dir / "settings.json", "w", encoding="utf-8") as f:
        json.dump({"log_level": "INFO"}, f)

    with open(claude_dir / "settings.local.json", "w", encoding="utf-8") as f:
        json.dump({"log_level": "DEBUG"}, f)

    loader = ConfigLoader(project_root=temp_project_dir)
    settings = loader.load()

    # local.json should win
    assert settings.log_level == "DEBUG"


def test_merge_nested_dicts(temp_project_dir: str) -> None:
    """验证嵌套字典合并"""
    claude_dir = Path(temp_project_dir) / ".my-claude"
    claude_dir.mkdir(parents=True)

    # Shared config with some llm settings
    with open(claude_dir / "settings.json", "w", encoding="utf-8") as f:
        json.dump({
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
            }
        }, f)

    # Local config overrides only model
    with open(claude_dir / "settings.local.json", "w", encoding="utf-8") as f:
        json.dump({
            "llm": {
                "model": "deepseek-chat",
            }
        }, f)

    loader = ConfigLoader(project_root=temp_project_dir)
    settings = loader.load()

    # Model should be overridden
    assert settings.llm.model == "deepseek-chat"
    # Other llm settings should be preserved
    assert settings.llm.provider == "openai"
    assert settings.llm.temperature == 0.7


def test_load_settings_convenience(temp_project_dir: str) -> None:
    """验证 load_settings 便捷函数"""
    settings = load_settings(project_root=temp_project_dir)

    assert isinstance(settings, settings.__class__)
    assert settings.llm.provider == "openai"


def test_invalid_json_ignored(temp_project_dir: str) -> None:
    """验证无效 JSON 被忽略"""
    claude_dir = Path(temp_project_dir) / ".my-claude"
    claude_dir.mkdir(parents=True)

    # Write invalid JSON
    with open(claude_dir / "settings.json", "w", encoding="utf-8") as f:
        f.write("{ invalid json }")

    loader = ConfigLoader(project_root=temp_project_dir)
    settings = loader.load()

    # Should fall back to defaults
    assert settings.llm.provider == "openai"


class TestEnvironmentVariables:
    """环境变量配置测试"""

    def test_openrouter_api_key(self, temp_project_dir: str, monkeypatch) -> None:
        """验证 OPENROUTER_API_KEY 环境变量"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        assert settings.llm.provider == "requests"
        assert settings.llm.api_key == "sk-or-test-key"
        assert settings.llm.api_base == "https://openrouter.ai/api/v1"

    def test_openrouter_with_custom_model(self, temp_project_dir: str, monkeypatch) -> None:
        """验证 OPENROUTER_API_KEY 和 OPENROUTER_MODEL 环境变量"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
        monkeypatch.setenv("OPENROUTER_MODEL", "deepseek/deepseek-r1:70b")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        assert settings.llm.provider == "requests"
        assert settings.llm.api_key == "sk-or-test-key"
        assert settings.llm.model == "deepseek/deepseek-r1:70b"

    def test_openrouter_with_custom_base_url(self, temp_project_dir: str, monkeypatch) -> None:
        """验证自定义 OPENROUTER_BASE_URL"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
        monkeypatch.setenv("OPENROUTER_BASE_URL", "https://custom.openrouter.ai/v1")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        assert settings.llm.provider == "requests"
        assert settings.llm.api_base == "https://custom.openrouter.ai/v1"

    def test_deepseek_env_vars(self, temp_project_dir: str, monkeypatch) -> None:
        """验证 DEEPSEEK_* 环境变量"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
        monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        assert settings.llm.provider == "requests"
        assert settings.llm.api_key == "sk-deepseek-test"
        assert settings.llm.api_base == "https://api.deepseek.com/v1"
        assert settings.llm.model == "deepseek-chat"

    def test_openai_env_vars(self, temp_project_dir: str, monkeypatch) -> None:
        """验证 OPENAI_* 环境变量"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        assert settings.llm.provider == "openai"
        assert settings.llm.api_key == "sk-openai-test"
        assert settings.llm.model == "gpt-4"

    def test_env_vars_override_config_files(self, temp_project_dir: str, monkeypatch) -> None:
        """验证环境变量覆盖配置文件"""
        claude_dir = Path(temp_project_dir) / ".my-claude"
        claude_dir.mkdir(parents=True)

        # Create config file
        with open(claude_dir / "settings.json", "w", encoding="utf-8") as f:
            json.dump({"llm": {"model": "gpt-4"}}, f)

        # Set env var to override
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        monkeypatch.setenv("OPENROUTER_MODEL", "deepseek/deepseek-r1:70b")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        # Env var should win
        assert settings.llm.model == "deepseek/deepseek-r1:70b"

    def test_provider_priority_openrouter_first(self, temp_project_dir: str, monkeypatch) -> None:
        """验证 provider 优先级: OpenRouter > DeepSeek > OpenAI"""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        # OpenRouter should win
        assert settings.llm.provider == "requests"
        assert settings.llm.api_key == "sk-or-test"


class TestEnvFile:
    """测试 .env 文件解析"""

    def test_parse_env_file_simple(self) -> None:
        """验证简单的 .env 文件解析"""
        from pathlib import Path
        import tempfile
        from claude_code.config.loader import _parse_env_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("KEY1=value1\n")
            f.write("KEY2=value2\n")
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("KEY3=value3\n")
            temp_path = Path(f.name)

        try:
            result = _parse_env_file(temp_path)
            assert result == {
                "KEY1": "value1",
                "KEY2": "value2",
                "KEY3": "value3",
            }
        finally:
            temp_path.unlink()

    def test_parse_env_file_with_quotes(self) -> None:
        """验证带引号的 .env 文件解析"""
        from pathlib import Path
        import tempfile
        from claude_code.config.loader import _parse_env_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write('KEY1="value with spaces"\n')
            f.write("KEY2='value with single quotes'\n")
            f.write("KEY3=value_without_quotes\n")
            temp_path = Path(f.name)

        try:
            result = _parse_env_file(temp_path)
            assert result["KEY1"] == "value with spaces"
            assert result["KEY2"] == "value with single quotes"
            assert result["KEY3"] == "value_without_quotes"
        finally:
            temp_path.unlink()

    def test_parse_env_file_empty(self) -> None:
        """验证空 .env 文件解析"""
        from pathlib import Path
        import tempfile
        from claude_code.config.loader import _parse_env_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# Only comments\n")
            f.write("\n")
            temp_path = Path(f.name)

        try:
            result = _parse_env_file(temp_path)
            assert result == {}
        finally:
            temp_path.unlink()

    def test_parse_env_file_nonexistent(self) -> None:
        """验证不存在的 .env 文件解析"""
        from pathlib import Path
        from claude_code.config.loader import _parse_env_file

        result = _parse_env_file(Path("/nonexistent/path/.env"))
        assert result == {}

    def test_load_from_dotenv_file(self, temp_project_dir: str) -> None:
        """验证从 .env 文件加载配置"""
        env_path = Path(temp_project_dir) / ".env"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("OPENROUTER_API_KEY=sk-or-from-env\n")
            f.write("OPENROUTER_MODEL=deepseek/deepseek-r1:70b\n")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        assert settings.llm.provider == "requests"
        assert settings.llm.api_key == "sk-or-from-env"
        assert settings.llm.model == "deepseek/deepseek-r1:70b"

    def test_load_from_env_local_overrides_env(self, temp_project_dir: str) -> None:
        """验证 .env.local 覆盖 .env"""
        env_path = Path(temp_project_dir) / ".env"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("OPENROUTER_API_KEY=sk-or-from-env\n")
            f.write("OPENROUTER_MODEL=model-from-env\n")

        env_local_path = Path(temp_project_dir) / ".env.local"
        with open(env_local_path, "w", encoding="utf-8") as f:
            f.write("OPENROUTER_MODEL=model-from-local\n")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        # API key from .env
        assert settings.llm.api_key == "sk-or-from-env"
        # Model from .env.local (overrides .env)
        assert settings.llm.model == "model-from-local"

    def test_system_env_overrides_env_files(self, temp_project_dir: str, monkeypatch) -> None:
        """验证系统环境变量覆盖 .env 文件"""
        # System env should override - set it first
        monkeypatch.setenv("OPENROUTER_MODEL", "model-from-system")

        env_path = Path(temp_project_dir) / ".env"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("OPENROUTER_API_KEY=sk-or-from-env\n")
            f.write("OPENROUTER_MODEL=model-from-env\n")

        loader = ConfigLoader(project_root=temp_project_dir)
        settings = loader.load()

        # API key from .env (not in system env)
        assert settings.llm.api_key == "sk-or-from-env"
        # Model from system env (overrides .env)
        assert settings.llm.model == "model-from-system"
