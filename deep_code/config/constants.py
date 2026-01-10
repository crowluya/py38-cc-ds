"""
Configuration constants for DeepCode.

Centralized constants for directory names and paths.
"""

from pathlib import Path
from typing import Optional

# Application name (used for directory naming)
APP_NAME = "pycc"

# Directory names (relative to home or project root)
_USER_CONFIG_DIR = f".{APP_NAME}"
_PROJECT_CONFIG_DIR = f".{APP_NAME}"

# Subdirectory names
COMMANDS_DIR = "commands"
HOOKS_DIR = "hooks"
CHECKPOINTS_DIR = "checkpoints"

# Config file names
SETTINGS_FILE = "settings.json"
SETTINGS_LOCAL_FILE = "settings.local.json"


def get_user_config_dir() -> Path:
    """
    Get user config directory path.

    Returns:
        Path to ~/.pycc
    """
    return Path.home() / _USER_CONFIG_DIR


def get_project_config_dir(project_root: Optional[Path] = None) -> Path:
    """
    Get project config directory path.

    Args:
        project_root: Project root directory. If None, uses current directory.

    Returns:
        Path to .pycc in project
    """
    if project_root is None:
        project_root = Path.cwd()
    return project_root / _PROJECT_CONFIG_DIR


def get_user_commands_dir() -> Path:
    """Get user commands directory path (~/.pycc/commands)."""
    return get_user_config_dir() / COMMANDS_DIR


def get_user_hooks_dir() -> Path:
    """Get user hooks directory path (~/.pycc/hooks)."""
    return get_user_config_dir() / HOOKS_DIR


def get_project_commands_dir(project_root: Optional[Path] = None) -> Path:
    """Get project commands directory path (.pycc/commands)."""
    return get_project_config_dir(project_root) / COMMANDS_DIR


def get_project_hooks_dir(project_root: Optional[Path] = None) -> Path:
    """Get project hooks directory path (.pycc/hooks)."""
    return get_project_config_dir(project_root) / HOOKS_DIR


def get_project_checkpoints_dir(project_root: Optional[Path] = None) -> Path:
    """Get project checkpoints directory path (.pycc/checkpoints)."""
    return get_project_config_dir(project_root) / CHECKPOINTS_DIR


# Backward compatibility aliases (string paths)
USER_CONFIG_DIR = _USER_CONFIG_DIR
PROJECT_CONFIG_DIR = _PROJECT_CONFIG_DIR
USER_COMMANDS_DIR = f"{_USER_CONFIG_DIR}/{COMMANDS_DIR}"
USER_HOOKS_DIR = f"{_USER_CONFIG_DIR}/{HOOKS_DIR}"
PROJECT_COMMANDS_DIR = f"{_PROJECT_CONFIG_DIR}/{COMMANDS_DIR}"
PROJECT_HOOKS_DIR = f"{_PROJECT_CONFIG_DIR}/{HOOKS_DIR}"
PROJECT_CHECKPOINTS_DIR = f"{_PROJECT_CONFIG_DIR}/{CHECKPOINTS_DIR}"
