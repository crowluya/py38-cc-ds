"""
Configuration module for Claude Code Python MVP.

Contains settings loader, path utilities, and constants.
"""

from pathlib import Path

from claude_code.config.constants import (
    APP_NAME,
    CHECKPOINTS_DIR,
    COMMANDS_DIR,
    HOOKS_DIR,
    PROJECT_CHECKPOINTS_DIR,
    PROJECT_COMMANDS_DIR,
    PROJECT_CONFIG_DIR,
    PROJECT_HOOKS_DIR,
    SETTINGS_FILE,
    SETTINGS_LOCAL_FILE,
    USER_COMMANDS_DIR,
    USER_CONFIG_DIR,
    USER_HOOKS_DIR,
    get_user_config_dir,
    get_project_config_dir,
)
from claude_code.config.loader import load_settings
from claude_code.config.paths import get_project_root


def get_user_home() -> Path:
    """
    Get user home directory.

    Returns:
        Path to user home directory
    """
    return Path.home()


__all__ = [
    # Constants
    "APP_NAME",
    "USER_CONFIG_DIR",
    "PROJECT_CONFIG_DIR",
    "COMMANDS_DIR",
    "HOOKS_DIR",
    "CHECKPOINTS_DIR",
    "USER_COMMANDS_DIR",
    "USER_HOOKS_DIR",
    "PROJECT_COMMANDS_DIR",
    "PROJECT_HOOKS_DIR",
    "PROJECT_CHECKPOINTS_DIR",
    "SETTINGS_FILE",
    "SETTINGS_LOCAL_FILE",
    # Functions
    "load_settings",
    "get_project_root",
    "get_user_home",
    "get_user_config_dir",
    "get_project_config_dir",
]
