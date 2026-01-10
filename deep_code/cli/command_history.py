"""
Command History Module (CMD-017, CMD-018)

Python 3.8.10 compatible
Provides command history persistence and quick re-execution.
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class CommandEntry:
    """A single command history entry."""

    command: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    return_code: int = 0
    working_dir: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "command": self.command,
            "timestamp": self.timestamp,
            "return_code": self.return_code,
            "working_dir": self.working_dir,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CommandEntry":
        """Create from dictionary."""
        return cls(
            command=data.get("command", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            return_code=data.get("return_code", 0),
            working_dir=data.get("working_dir", ""),
        )


class CommandHistory:
    """
    Persistent command history storage.

    Stores executed commands in .deepcode/command_history.json
    Supports:
    - Adding new commands
    - Retrieving recent commands
    - Quick re-execution patterns (!, !!, !-N, !prefix)
    """

    DEFAULT_MAX_ENTRIES = 1000

    def __init__(
        self,
        project_root: Optional[str] = None,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ) -> None:
        """
        Initialize command history.

        Args:
            project_root: Project root directory
            max_entries: Maximum number of entries to keep
        """
        if project_root:
            self._root = Path(project_root)
        else:
            self._root = Path.cwd()

        self._history_file = self._root / ".deepcode" / "command_history.json"
        self._max_entries = max_entries
        self._entries: List[CommandEntry] = []
        self._load()

    def _ensure_dir(self) -> None:
        """Ensure .deepcode directory exists."""
        self._history_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        """Load history from file."""
        if not self._history_file.exists():
            self._entries = []
            return

        try:
            with open(self._history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._entries = [CommandEntry.from_dict(e) for e in data.get("entries", [])]
        except (json.JSONDecodeError, IOError):
            self._entries = []

    def _save(self) -> None:
        """Save history to file."""
        self._ensure_dir()

        # Trim to max entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        data = {"entries": [e.to_dict() for e in self._entries]}

        try:
            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    def add(
        self,
        command: str,
        return_code: int = 0,
        working_dir: Optional[str] = None,
    ) -> None:
        """
        Add a command to history.

        Args:
            command: Command that was executed
            return_code: Exit code of the command
            working_dir: Working directory when executed
        """
        entry = CommandEntry(
            command=command,
            return_code=return_code,
            working_dir=working_dir or str(self._root),
        )
        self._entries.append(entry)
        self._save()

    def get_recent(self, limit: int = 20) -> List[CommandEntry]:
        """
        Get recent commands.

        Args:
            limit: Maximum number of commands to return

        Returns:
            List of recent command entries (newest first)
        """
        return list(reversed(self._entries[-limit:]))

    def get_last(self) -> Optional[CommandEntry]:
        """
        Get the last executed command.

        Returns:
            Last command entry or None
        """
        if self._entries:
            return self._entries[-1]
        return None

    def get_by_index(self, index: int) -> Optional[CommandEntry]:
        """
        Get command by negative index (e.g., -1 for last, -2 for second last).

        Args:
            index: Negative index

        Returns:
            Command entry or None
        """
        if not self._entries:
            return None

        try:
            return self._entries[index]
        except IndexError:
            return None

    def search_prefix(self, prefix: str) -> Optional[CommandEntry]:
        """
        Find most recent command starting with prefix.

        Args:
            prefix: Command prefix to search for

        Returns:
            Most recent matching command or None
        """
        for entry in reversed(self._entries):
            if entry.command.startswith(prefix):
                return entry
        return None

    def search_contains(self, substring: str) -> List[CommandEntry]:
        """
        Find commands containing substring.

        Args:
            substring: Substring to search for

        Returns:
            List of matching commands (newest first)
        """
        matches = []
        for entry in reversed(self._entries):
            if substring in entry.command:
                matches.append(entry)
        return matches

    def clear(self) -> None:
        """Clear all history."""
        self._entries = []
        self._save()

    def __len__(self) -> int:
        """Return number of entries."""
        return len(self._entries)


# CMD-018: Quick re-execution patterns
def parse_history_reference(
    input_text: str,
    history: CommandHistory,
) -> Optional[str]:
    """
    Parse history reference and return the actual command.

    Supports:
    - !! : Last command
    - !-N : N-th last command (e.g., !-2 for second last)
    - !N : N-th command in history (1-indexed)
    - !prefix : Most recent command starting with prefix

    Args:
        input_text: User input (e.g., "!!", "!-2", "!git")
        history: CommandHistory instance

    Returns:
        Resolved command string or None if not a history reference
    """
    text = input_text.strip()

    # Not a history reference
    if not text.startswith("!"):
        return None

    # !! - repeat last command
    if text == "!!":
        entry = history.get_last()
        return entry.command if entry else None

    # !-N - N-th last command
    match = re.match(r"^!-(\d+)$", text)
    if match:
        n = int(match.group(1))
        entry = history.get_by_index(-n)
        return entry.command if entry else None

    # !N - N-th command (1-indexed)
    match = re.match(r"^!(\d+)$", text)
    if match:
        n = int(match.group(1))
        if 1 <= n <= len(history):
            entry = history._entries[n - 1]
            return entry.command
        return None

    # !prefix - most recent command starting with prefix
    # Must have at least one character after !
    if len(text) > 1:
        prefix = text[1:]
        # Skip if it looks like a regular command (has space)
        if " " in prefix:
            return None
        entry = history.search_prefix(prefix)
        return entry.command if entry else None

    return None


def is_history_reference(input_text: str) -> bool:
    """
    Check if input is a history reference.

    Args:
        input_text: User input

    Returns:
        True if input is a history reference pattern
    """
    text = input_text.strip()

    if not text.startswith("!"):
        return False

    # !!
    if text == "!!":
        return True

    # !-N
    if re.match(r"^!-\d+$", text):
        return True

    # !N
    if re.match(r"^!\d+$", text):
        return True

    # !prefix (no space, at least one char)
    if len(text) > 1 and " " not in text:
        return True

    return False
