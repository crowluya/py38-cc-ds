"""
Path utilities for Windows 7 + cross-platform compatibility

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Features:
- Cross-platform path handling (Windows/Unix)
- User directory expansion (~ and %USERPROFILE%)
- Path normalization
"""

import os
import sys
from pathlib import Path
from typing import Optional


def expand_user_path(path: str) -> str:
    """
    Expand user directory in path.

    Handles both Unix (~) and Windows (%USERPROFILE%) conventions.

    Args:
        path: Path string that may contain ~ or %USERPROFILE%

    Returns:
        Expanded path string
    """
    if not path:
        return path

    # First handle Windows environment variables
    expanded = os.path.expandvars(path)

    # Then handle Unix-style ~ expansion
    expanded = os.path.expanduser(expanded)

    return expanded


def normalize_path(path: str) -> str:
    """
    Normalize path for cross-platform use.

    Converts path separators to the platform's native format.

    Args:
        path: Path string

    Returns:
        Normalized path string
    """
    if not path:
        return path

    # Expand user first
    expanded = expand_user_path(path)

    # Use pathlib for normalization
    normalized = str(Path(expanded).resolve())

    return normalized


def get_home_directory() -> str:
    """
    Get user home directory.

    Works on both Windows and Unix-like systems.

    Returns:
        Home directory path
    """
    return str(Path.home())


def get_config_directory() -> str:
    """
    Get Claude Code configuration directory.

    Returns:
        Config directory path (~/.claude)
    """
    home = get_home_directory()
    return str(Path(home) / ".claude")


def ensure_directory(path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        Path to the directory
    """
    expanded = expand_user_path(path)
    dir_path = Path(expanded)

    dir_path.mkdir(parents=True, exist_ok=True)

    return str(dir_path)


def is_absolute_path(path: str) -> bool:
    """
    Check if path is absolute.

    Args:
        path: Path string

    Returns:
        True if path is absolute
    """
    expanded = expand_user_path(path)
    return Path(expanded).is_absolute()


def join_paths(*parts: str) -> str:
    """
    Join path parts using pathlib.

    Args:
        *parts: Path parts to join

    Returns:
        Joined path string
    """
    if not parts:
        return "."

    result = Path(parts[0])
    for part in parts[1:]:
        result = result / part

    return str(result)


class PathResolver:
    """
    Path resolution utility for cross-platform paths.

    Handles Windows 7 + Unix compatibility.
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize PathResolver.

        Args:
            base_dir: Base directory for relative paths
        """
        self._base_dir = normalize_path(base_dir) if base_dir else None

    def resolve(self, path: str) -> str:
        """
        Resolve a path relative to base directory.

        Args:
            path: Path to resolve (can be absolute or relative)

        Returns:
            Resolved absolute path
        """
        expanded = expand_user_path(path)

        if is_absolute_path(expanded):
            return normalize_path(expanded)

        if self._base_dir:
            return join_paths(self._base_dir, expanded)

        return normalize_path(expanded)

    @property
    def base_dir(self) -> Optional[str]:
        """Get the base directory."""
        return self._base_dir

    def set_base_dir(self, base_dir: str) -> None:
        """Set the base directory."""
        self._base_dir = normalize_path(base_dir)


def get_project_root() -> Optional[str]:
    """
    Detect project root directory by looking for .claude directory.

    Returns:
        Project root path or None if not found
    """
    current = Path.cwd()

    # Search up the directory tree
    for _ in range(20):  # Limit search depth
        claude_dir = current / ".claude"
        if claude_dir.exists() and claude_dir.is_dir():
            return str(current)

        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    return None
