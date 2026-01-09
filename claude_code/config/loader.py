"""
Configuration loader with layered priority

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Priority order (highest to lowest):
1. Environment variables
2. CLI arguments
3. Project .env.local file
4. Project .env file
5. Project local: {PROJECT_CONFIG_DIR}/{SETTINGS_LOCAL_FILE}
6. Project shared: {PROJECT_CONFIG_DIR}/{SETTINGS_FILE}
7. User global: ~/{USER_CONFIG_DIR}/{SETTINGS_FILE}
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


def _parse_env_file(path: Path) -> Dict[str, str]:
    """
    Parse a .env file into a dictionary.

    Args:
        path: Path to .env file

    Returns:
        Dictionary of environment variables

    Supports:
    - KEY=value
    - KEY="value with spaces"
    - KEY='value with spaces'
    - # Comments (ignored)
    - Empty lines (ignored)
    """
    env_vars: Dict[str, str] = {}

    if not path.exists():
        return env_vars

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()

                    # Remove quotes if present
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    env_vars[key] = value
    except (IOError, OSError):
        pass

    return env_vars


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
        Load config from environment variables and .env files.

        Priority (highest to lowest):
        1. System environment variables
        2. .env.local file (project root)
        3. .env file (project root)

        Provider detection priority:
        1. OPENROUTER_API_KEY → requests provider
        2. DEEPSEEK_API_KEY → requests provider
        3. OPENAI_API_KEY → openai provider

        Returns:
            Config dict or None if no env vars set
        """
        # Collect env vars from all sources (merged, later sources override)
        merged_env: Dict[str, str] = {}

        # Layer 1: .env file (lowest priority)
        if self._project_root:
            env_file = self._project_root / ".env"
            merged_env.update(_parse_env_file(env_file))

        # Layer 2: .env.local file (higher priority)
        if self._project_root:
            env_local_file = self._project_root / ".env.local"
            merged_env.update(_parse_env_file(env_local_file))

        # Layer 3: System environment variables (highest priority - overrides all)
        merged_env.update(os.environ)

        env_vars: Dict[str, Any] = {}

        # First, detect which provider to use (priority order)
        provider_configs = []

        # Check for OpenRouter
        if "OPENROUTER_API_KEY" in merged_env:
            provider_configs.append({
                "name": "openrouter",
                "provider": "requests",
                "api_key": merged_env.get("OPENROUTER_API_KEY"),
                "api_base": merged_env.get("OPENROUTER_BASE_URL") or merged_env.get("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1",
                "model": merged_env.get("OPENROUTER_MODEL") or merged_env.get("DEEPSEEK_MODEL") or merged_env.get("OPENAI_MODEL") or "deepseek/deepseek-r1:70b",
            })

        # Check for DeepSeek
        if "DEEPSEEK_API_KEY" in merged_env or "DEEPSEEK_BASE_URL" in merged_env:
            provider_configs.append({
                "name": "deepseek",
                "provider": "requests",
                "api_key": merged_env.get("DEEPSEEK_API_KEY"),
                "api_base": merged_env.get("DEEPSEEK_BASE_URL") or merged_env.get("OPENAI_BASE_URL"),
                "model": merged_env.get("DEEPSEEK_MODEL") or merged_env.get("OPENAI_MODEL"),
            })

        # Check for OpenAI
        if "OPENAI_API_KEY" in merged_env:
            provider_configs.append({
                "name": "openai",
                "provider": "openai",
                "api_key": merged_env.get("OPENAI_API_KEY"),
                "api_base": merged_env.get("OPENAI_BASE_URL"),
                "model": merged_env.get("OPENAI_MODEL"),
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
            value = merged_env.get(env_var)
            if value is not None:
                # Type conversion for boolean and numeric values
                if env_var == "VERIFY_SSL":
                    value = value.lower() in ("true", "1", "yes", "on")
                elif env_var == "MAX_TOKENS":
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                elif env_var == "TEMPERATURE":
                    try:
                        value = float(value)
                    except ValueError:
                        continue

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
        Load user global config from ~/.pycc/settings.json.

        Returns:
            Config dict or None if not found
        """
        config_path = get_user_config_dir() / SETTINGS_FILE
        return self._load_json_file(config_path)

    def _load_project_shared_config(self) -> Optional[Dict[str, Any]]:
        """
        Load project shared config from .pycc/settings.json.

        Returns:
            Config dict or None if not found
        """
        if not self._project_root:
            return None

        config_path = get_project_config_dir(self._project_root) / SETTINGS_FILE
        return self._load_json_file(config_path)

    def _load_project_local_config(self) -> Optional[Dict[str, Any]]:
        """
        Load project local config from .pycc/settings.local.json.

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
        project_root: Project root directory path (auto-detected if None)
        cli_overrides: Optional CLI argument overrides

    Returns:
        Merged Settings instance
    """
    # Auto-detect project root if not provided
    if project_root is None:
        project_root = _find_project_root_auto()

    loader = ConfigLoader(project_root)
    return loader.load(cli_overrides)


def _find_project_root_auto() -> Optional[str]:
    """
    Auto-detect project root by looking for markers.

    Searches upward from current directory.

    Returns:
        Project root path as string, or None if not found
    """
    from pathlib import Path as PathLib

    cwd = PathLib.cwd()

    # Search upward from current directory
    for path in [cwd] + list(cwd.parents):
        # Check for project markers
        if (path / ".env.local").exists():
            return str(path)
        if (path / ".env").exists():
            return str(path)
        if (path / ".pycc").exists():
            return str(path)
        if (path / "pyproject.toml").exists():
            return str(path)
        if (path / "setup.py").exists():
            return str(path)
        if (path / ".git").exists():
            return str(path)

    return None


__all__ = [
    "ConfigLoader",
    "load_settings",
    "_parse_env_file",
]
