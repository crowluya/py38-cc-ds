"""
File Completion Module (CMD-005 to CMD-007)

Python 3.8.10 compatible
Provides file/directory completion for @ references.
"""

import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


def fuzzy_match(pattern: str, text: str) -> Tuple[bool, int]:
    """
    Fuzzy match pattern against text.

    Supports:
    - Substring matching
    - Camel case matching (e.g., "gc" matches "getUserConfig")
    - Underscore matching (e.g., "gc" matches "get_config")

    Args:
        pattern: Pattern to match
        text: Text to match against

    Returns:
        Tuple of (matched, score). Higher score = better match.
    """
    if not pattern:
        return True, 0

    pattern_lower = pattern.lower()
    text_lower = text.lower()

    # Exact prefix match (highest score)
    if text_lower.startswith(pattern_lower):
        return True, 1000 - len(text)

    # Substring match
    if pattern_lower in text_lower:
        idx = text_lower.index(pattern_lower)
        return True, 500 - idx - len(text)

    # Fuzzy character match
    pattern_idx = 0
    score = 0
    last_match_idx = -1

    for i, char in enumerate(text_lower):
        if pattern_idx < len(pattern_lower) and char == pattern_lower[pattern_idx]:
            # Bonus for consecutive matches
            if last_match_idx == i - 1:
                score += 10
            # Bonus for matching after separator
            if i > 0 and text[i - 1] in "._-/\\":
                score += 20
            # Bonus for matching uppercase (camelCase)
            if i > 0 and text[i].isupper():
                score += 15

            pattern_idx += 1
            last_match_idx = i
            score += 1

    if pattern_idx == len(pattern_lower):
        return True, score - len(text)

    return False, 0


class FileCompleter(Completer):
    """
    Completer for file and directory paths.

    Triggers on @ prefix for context injection syntax.
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        only_directories: bool = False,
        ignore_patterns: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize file completer.

        Args:
            project_root: Root directory for relative paths
            only_directories: Only complete directories
            ignore_patterns: Patterns to ignore (e.g., [".git", "__pycache__"])
        """
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._only_directories = only_directories
        self._ignore_patterns = ignore_patterns or [
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            ".deepcode",
            "*.pyc",
            "*.pyo",
            ".DS_Store",
        ]

    def _should_ignore(self, name: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self._ignore_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False

    def _list_entries(self, directory: Path, prefix: str = "") -> List[Tuple[str, bool]]:
        """
        List directory entries.

        Args:
            directory: Directory to list
            prefix: Prefix filter

        Returns:
            List of (name, is_directory) tuples
        """
        entries = []

        try:
            for entry in directory.iterdir():
                name = entry.name

                if self._should_ignore(name):
                    continue

                if prefix and not fuzzy_match(prefix, name)[0]:
                    continue

                is_dir = entry.is_dir()

                if self._only_directories and not is_dir:
                    continue

                entries.append((name, is_dir))
        except (PermissionError, OSError):
            pass

        return entries

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """
        Get completions for the current document.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects
        """
        text = document.text_before_cursor

        # Find @ trigger
        at_match = re.search(r"@([^\s]*)$", text)
        if not at_match:
            return

        path_text = at_match.group(1)
        start_position = -len(path_text)

        # Parse path
        if "/" in path_text:
            # Has directory component
            parts = path_text.rsplit("/", 1)
            dir_part = parts[0]
            file_prefix = parts[1] if len(parts) > 1 else ""

            # Resolve directory
            if dir_part.startswith("/"):
                # Absolute path
                base_dir = Path(dir_part)
            else:
                # Relative path
                base_dir = self._project_root / dir_part

            if not base_dir.is_dir():
                return

            entries = self._list_entries(base_dir, file_prefix)

            for name, is_dir in sorted(entries, key=lambda x: (not x[1], x[0])):
                matched, score = fuzzy_match(file_prefix, name)
                if matched:
                    display = f"{name}/" if is_dir else name
                    completion_text = f"{dir_part}/{display}"
                    yield Completion(
                        completion_text,
                        start_position=start_position,
                        display=display,
                        display_meta="dir" if is_dir else "file",
                    )
        else:
            # No directory component, complete from project root
            entries = self._list_entries(self._project_root, path_text)

            for name, is_dir in sorted(entries, key=lambda x: (not x[1], x[0])):
                matched, score = fuzzy_match(path_text, name)
                if matched:
                    display = f"{name}/" if is_dir else name
                    yield Completion(
                        display,
                        start_position=start_position,
                        display=display,
                        display_meta="dir" if is_dir else "file",
                    )


class SlashCommandCompleter(Completer):
    """Completer for slash commands."""

    COMMANDS = [
        ("/mode", "Switch mode: /mode default|plan|bypass"),
        ("/plan", "Switch to plan mode"),
        ("/help", "Show help"),
        ("/clear", "Clear conversation"),
        ("/history", "Show command history"),
        ("/reset", "Reset session"),
        ("/exit", "Exit"),
        ("/quit", "Exit"),
        ("/sessions", "List sessions"),
    ]

    MODE_ARGS = ["default", "plan", "bypass"]

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """Get completions for slash commands."""
        text = document.text_before_cursor.lstrip()

        if not text.startswith("/"):
            return

        parts = text.split()

        if len(parts) == 1:
            # Complete command name
            cmd = parts[0]
            for name, desc in self.COMMANDS:
                if name.startswith(cmd):
                    yield Completion(
                        name,
                        start_position=-len(cmd),
                        display=name,
                        display_meta=desc,
                    )
        elif len(parts) == 2 and parts[0].lower() in ("/mode", "/m"):
            # Complete mode argument
            arg = parts[1]
            for mode in self.MODE_ARGS:
                if mode.startswith(arg.lower()):
                    yield Completion(
                        mode,
                        start_position=-len(arg),
                        display=mode,
                    )


class CombinedCompleter(Completer):
    """Combines multiple completers."""

    def __init__(self, completers: List[Completer]) -> None:
        """
        Initialize combined completer.

        Args:
            completers: List of completers to combine
        """
        self._completers = completers

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """Get completions from all completers."""
        for completer in self._completers:
            yield from completer.get_completions(document, complete_event)


def create_completer(project_root: Optional[str] = None) -> Completer:
    """
    Create a combined completer for the CLI.

    Args:
        project_root: Project root directory

    Returns:
        Combined completer
    """
    return CombinedCompleter([
        FileCompleter(project_root=project_root),
        SlashCommandCompleter(),
    ])
