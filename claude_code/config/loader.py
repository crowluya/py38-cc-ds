"""
Configuration loader with layered priority

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Priority order (highest to lowest):
1. Environment variables
2. CLI arguments
3. Project local: {PROJECT_CONFIG_DIR}/{SETTINGS_LOCAL_FILE}
4. Project shared: {PROJECT_CONFIG_DIR}/{SETTINGS_FILE}
5. User global: ~/{USER_CONFIG_DIR}/{SETTINGS_FILE}
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from claude_code.config.constants import (
    SETTINGS_FILE,
    SETTINGS_LOCAL_FILE,
    get_project_config_dir,
    get_user_config_dir,
)
from claude_code.config.settings import Settings


class ConfigLoader:
    """
    Configuration loader with layered priority support.

    Loads and merges settings from multiple sources with proper priority.
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize ConfigLoader.

        Args:
            project_root: Project root directory path
        """
        self._project_root = Path(project_root) if project_root else None

    def load(self, cli_overrides: Optional[Dict[str, Any]] = None) -> Settings:
        """
        Load settings with full priority resolution.

        Args:
            cli_overrides: Optional CLI argument overrides (highest priority)

        Returns:
            Merged Settings instance
        """
        # Start with defaults
        settings = Settings()

        # Layer 5: User global config (lowest priority)
        user_config = self._load_user_global_config()
        if user_config:
            settings = Settings.from_dict(self._merge_dicts(
                settings.to_dict(),
                user_config
            ))

        # Layer 4: Project shared config
        project_config = self._load_project_shared_config()
        if project_config:
            settings = Settings.from_dict(self._merge_dicts(
                settings.to_dict(),
                project_config
            ))

        # Layer 3: Project local config
        local_config = self._load_project_local_config()
        if local_config:
            settings = Settings.from_dict(self._merge_dicts(
                settings.to_dict(),
                local_config
            ))

        # Layer 2: Environment variables
        env_config = self._load_env_config()
        if env_config:
            settings = Settings.from_dict(self._merge_dicts(
                settings.to_dict(),
                env_config
            ))

        # Layer 1: CLI overrides (highest priority)
        if cli_overrides:
            settings = Settings.from_dict(self._merge_dicts(
                settings.to_dict(),
                cli_overrides
            ))

        return settings

    def _load_env_config(self) -> Optional[Dict[str, Any]]:
        """
        Load config from environment variables.

        Provider detection priority:
        1. OPENROUTER_API_KEY → requests provider
        2. DEEPSEEK_API_KEY → requests provider
        3. OPENAI_API_KEY → openai provider

        Returns:
            Config dict or None if no env vars set
        """
        env_vars: Dict[str, Any] = {}

        # First, detect which provider to use (priority order)
        provider_configs = []

        # Check for OpenRouter
        if "OPENROUTER_API_KEY" in os.environ:
            provider_configs.append({
                "name": "openrouter",
                "provider": "requests",
                "api_key": os.environ.get("OPENROUTER_API_KEY"),
                "api_base": os.environ.get("OPENROUTER_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1",
                "model": os.environ.get("OPENROUTER_MODEL") or os.environ.get("DEEPSEEK_MODEL") or os.environ.get("OPENAI_MODEL") or "deepseek/deepseek-r1:70b",
            })

        # Check for DeepSeek
        if "DEEPSEEK_API_KEY" in os.environ or "DEEPSEEK_BASE_URL" in os.environ:
            provider_configs.append({
                "name": "deepseek",
                "provider": "requests",
                "api_key": os.environ.get("DEEPSEEK_API_KEY"),
                "api_base": os.environ.get("DEEPSEEK_BASE_URL") or os.environ.get("OPENAI_BASE_URL"),
                "model": os.environ.get("DEEPSEEK_MODEL") or os.environ.get("OPENAI_MODEL"),
            })

        # Check for OpenAI
        if "OPENAI_API_KEY" in os.environ:
            provider_configs.append({
                "name": "openai",
                "provider": "openai",
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "api_base": os.environ.get("OPENAI_BASE_URL"),
                "model": os.environ.get("OPENAI_MODEL"),
            })

        # Use the first (highest priority) provider config
        if provider_configs:
            config = provider_configs[0]
            env_vars["llm"] = {
                "provider": config["provider"],
                "api_key": config["api_key"],
            }
            if config["api_base"]:
                env_vars["llm"]["api_base"] = config["api_base"]
            if config["model"]:
                env_vars["llm"]["model"] = config["model"]

        # Map other environment variables (non-provider specific)
        other_mappings = {
            "DEFAULT_PERMISSION_MODE": ("permissions", "default_mode"),
            "LOG_LEVEL": ("log_level",),
            "VERIFY_SSL": ("llm", "verify_ssl"),
            "CA_CERT_PATH": ("llm", "ca_cert"),
            "MAX_TOKENS": ("llm", "max_tokens"),
            "TEMPERATURE": ("llm", "temperature"),
        }

        for env_var, config_path in other_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Navigate nested dict path
                current = env_vars
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                # Set final value
                current[config_path[-1]] = value

        return env_vars if env_vars else None

    def _load_user_global_config(self) -> Optional[Dict[str, Any]]:
        """
        Load user global config from ~/.my-claude/settings.json.

        Returns:
            Config dict or None if not found
        """
        config_path = get_user_config_dir() / SETTINGS_FILE
        return self._load_json_file(config_path)

    def _load_project_shared_config(self) -> Optional[Dict[str, Any]]:
        """
        Load project shared config from .my-claude/settings.json.

        Returns:
            Config dict or None if not found
        """
        if not self._project_root:
            return None

        config_path = get_project_config_dir(self._project_root) / SETTINGS_FILE
        return self._load_json_file(config_path)

    def _load_project_local_config(self) -> Optional[Dict[str, Any]]:
        """
        Load project local config from .my-claude/settings.local.json.

        Returns:
            Config dict or None if not found
        """
        if not self._project_root:
            return None

        config_path = get_project_config_dir(self._project_root) / SETTINGS_LOCAL_FILE
        return self._load_json_file(config_path)

    def _load_json_file(self, path: Path) -> Optional[Dict[str, Any]]:
        """
        Load JSON file with error handling.

        Args:
            path: Path to JSON file

        Returns:
            Parsed dict or None if file not found/invalid
        """
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            return None

    def _merge_dicts(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge two dictionaries recursively.

        Args:
            base: Base dictionary
            override: Override dictionary (takes priority)

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._merge_dicts(result[key], value)
            else:
                # Override with new value
                result[key] = value

        return result


def load_settings(
    project_root: Optional[str] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> Settings:
    """
    Convenience function to load settings.

    Args:
        project_root: Project root directory path
        cli_overrides: Optional CLI argument overrides

    Returns:
        Merged Settings instance
    """
    loader = ConfigLoader(project_root)
    return loader.load(cli_overrides)
