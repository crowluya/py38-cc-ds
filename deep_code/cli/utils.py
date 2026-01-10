"""
CLI utility functions for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import logging
import os
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_LOGGER = logging.getLogger("pycc")


def get_terminal_width(app=None, default: int = 100, min_width: int = 60) -> int:
    """
    Get terminal width with fallback.

    Args:
        app: Optional prompt_toolkit Application instance
        default: Default width if detection fails
        min_width: Minimum width to return

    Returns:
        Terminal width in columns
    """
    cols = default
    if app is not None:
        try:
            cols = app.output.get_size().columns
        except Exception:
            pass
    if cols == default:
        try:
            cols = shutil.get_terminal_size((default, 24)).columns
        except Exception:
            cols = default
    return max(min_width, cols)


def coerce_log_level(level: Optional[str]) -> int:
    """
    Convert log level string to logging constant.

    Args:
        level: Log level string (e.g., "DEBUG", "INFO", "WARNING")

    Returns:
        Logging level constant (e.g., logging.DEBUG)
    """
    if not level:
        return logging.INFO
    s = str(level).strip().upper()
    if s in ("CRITICAL", "FATAL"):
        return logging.CRITICAL
    if s == "ERROR":
        return logging.ERROR
    if s in ("WARN", "WARNING"):
        return logging.WARNING
    if s == "INFO":
        return logging.INFO
    if s == "DEBUG":
        return logging.DEBUG
    try:
        return int(s)
    except Exception:
        return logging.INFO


def init_file_logging(project_root: str, level: Optional[str]) -> None:
    """
    Initialize file logging with rotation.

    Args:
        project_root: Project root directory path
        level: Log level string
    """
    try:
        root = Path(project_root)
        log_dir = root / ".pycc"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "pycc.log"

        lvl = coerce_log_level(level)
        logger = _LOGGER
        logger.setLevel(lvl)

        for h in list(logger.handlers):
            try:
                logger.removeHandler(h)
            except Exception:
                pass

        handler = RotatingFileHandler(
            str(log_path),
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setLevel(lvl)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

        logger.info("logging initialized: level=%s path=%s", logging.getLevelName(lvl), str(log_path))
    except Exception:
        pass


def find_project_root() -> Optional[str]:
    """
    Find project root by looking for .env, .env.local, or .pycc directory.

    Searches upward from current directory until finding a project marker.

    Returns:
        Project root path as string, or None if not found
    """
    cwd = Path.cwd()

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


def resolve_under_root(project_root: str, user_path: str) -> str:
    """
    Resolve a user-provided path under the project root.

    Ensures the resolved path does not escape the project root directory.

    Args:
        project_root: Project root directory path
        user_path: User-provided path (relative or absolute)

    Returns:
        Resolved absolute path as string

    Raises:
        ValueError: If the path escapes the project root
    """
    base = Path(project_root).resolve()
    # Normalize Windows-style backslashes to forward slashes for cross-platform
    # path traversal detection (e.g., "..\README.md" -> "../README.md")
    normalized_path = user_path.replace("\\", "/")
    p = Path(normalized_path)
    if not p.is_absolute():
        p = (base / p).resolve()
    else:
        p = p.resolve()
    try:
        p.relative_to(base)
    except Exception:
        raise ValueError(f"path escapes project_root: {user_path}")
    return str(p)


def format_dir_listing(root: str, recursive: bool, max_entries: int) -> str:
    """
    Format a directory listing.

    Args:
        root: Root directory path
        recursive: Whether to list recursively
        max_entries: Maximum number of entries to return

    Returns:
        Formatted directory listing string
    """
    root_p = Path(root)
    if not root_p.exists():
        return f"Error: directory not found: {root}"
    if not root_p.is_dir():
        return f"Error: not a directory: {root}"

    items = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            filenames.sort()
            for dn in dirnames:
                items.append(str(Path(dirpath, dn)))
                if len(items) >= max_entries:
                    break
            if len(items) >= max_entries:
                break
            for fn in filenames:
                items.append(str(Path(dirpath, fn)))
                if len(items) >= max_entries:
                    break
            if len(items) >= max_entries:
                break
    else:
        for child in sorted(root_p.iterdir(), key=lambda x: x.name.lower()):
            items.append(str(child))
            if len(items) >= max_entries:
                break

    rel_items = []
    base = root_p
    for it in items:
        try:
            rel_items.append(str(Path(it).relative_to(base)))
        except Exception:
            rel_items.append(str(Path(it)))

    suffix = "\n... (truncated)" if len(items) >= max_entries else ""
    return "\n".join(rel_items) + suffix


def truncate_lines(s: str, max_lines: int = 30) -> str:
    """
    Truncate a string to a maximum number of lines.

    Args:
        s: Input string
        max_lines: Maximum number of lines to keep

    Returns:
        Truncated string with indicator if truncated
    """
    lines = s.splitlines()
    if len(lines) <= max_lines:
        return s
    shown = "\n".join(lines[:max_lines])
    remain = len(lines) - max_lines
    return shown + f"\n… +{remain} lines"


def extract_first_json_object(text: str) -> str:
    """
    Extract the first JSON object or array from text.

    Handles markdown code blocks and finds the first { or [ character.

    Args:
        text: Input text potentially containing JSON

    Returns:
        Extracted JSON string, or empty string if not found
    """
    s = text.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1:]
        last_fence = s.rfind("```")
        if last_fence != -1:
            s = s[:last_fence]
    s = s.strip()
    start = None
    for ch in ("{", "["):
        idx = s.find(ch)
        if idx != -1:
            start = idx if start is None else min(start, idx)
    if start is None:
        return ""
    s2 = s[start:]
    end_obj = s2.rfind("}")
    end_arr = s2.rfind("]")
    end = max(end_obj, end_arr)
    if end == -1:
        return ""
    return s2[: end + 1]
