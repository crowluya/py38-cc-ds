"""
Configuration loader with layered priority

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Priority order (highest to lowest):
1. CLI arguments
2. Project local: .claude/settings.local.json
3. Project shared: .claude/settings.json
4. User global: ~/.claude/settings.json
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

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

        # Layer 4: User global config (lowest priority)
        user_config = self._load_user_global_config()
        if user_config:
            settings = Settings.from_dict(self._merge_dicts(
                settings.to_dict(),
                user_config
            ))

        # Layer 3: Project shared config
        project_config = self._load_project_shared_config()
        if project_config:
            settings = Settings.from_dict(self._merge_dicts(
                settings.to_dict(),
                project_config
            ))

        # Layer 2: Project local config
        local_config = self._load_project_local_config()
        if local_config:
            settings = Settings.from_dict(self._merge_dicts(
                settings.to_dict(),
                local_config
            ))

        # Layer 1: CLI overrides (highest priority)
        if cli_overrides:
            settings = Settings.from_dict(self._merge_dicts(
                settings.to_dict(),
                cli_overrides
            ))

        return settings

    def _load_user_global_config(self) -> Optional[Dict[str, Any]]:
        """
        Load user global config from ~/.claude/settings.json.

        Returns:
            Config dict or None if not found
        """
        config_path = Path.home() / ".claude" / "settings.json"
        return self._load_json_file(config_path)

    def _load_project_shared_config(self) -> Optional[Dict[str, Any]]:
        """
        Load project shared config from .claude/settings.json.

        Returns:
            Config dict or None if not found
        """
        if not self._project_root:
            return None

        config_path = self._project_root / ".claude" / "settings.json"
        return self._load_json_file(config_path)

    def _load_project_local_config(self) -> Optional[Dict[str, Any]]:
        """
        Load project local config from .claude/settings.local.json.

        Returns:
            Config dict or None if not found
        """
        if not self._project_root:
            return None

        config_path = self._project_root / ".claude" / "settings.local.json"
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
