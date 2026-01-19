"""Integration with note-taking CLI."""

import subprocess
from typing import Optional

from ai_command_palette.core.registry import Command, CommandRegistry, CommandType


class NotesIntegration:
    """Integration with note-taking tools."""

    def __init__(self, notes_cli_path: Optional[str] = None):
        """Initialize notes integration."""
        self.notes_cli_path = notes_cli_path or "note"  # Default to 'note' command

    def register_commands(self, registry: CommandRegistry):
        """Register note-taking commands with the registry."""
        note_commands = [
            Command(
                name="note:create",
                command_type=CommandType.NOTE,
                description="Create a new note",
                command_template=f"{self.notes_cli_path} create {{title}}",
                category="Notes",
                tags=["note", "create", "new"],
                icon="📝",
            ),
            Command(
                name="note:search",
                command_type=CommandType.NOTE,
                description="Search notes",
                command_template=f"{self.notes_cli_path} search {{query}}",
                category="Notes",
                tags=["note", "search", "find"],
                icon="🔍",
            ),
            Command(
                name="note:edit",
                command_type=CommandType.NOTE,
                description="Edit a note",
                command_template=f"{self.notes_cli_path} edit {{title}}",
                category="Notes",
                tags=["note", "edit"],
                icon="✏️",
            ),
            Command(
                name="note:list",
                command_type=CommandType.NOTE,
                description="List all notes",
                command_template=f"{self.notes_cli_path} list",
                category="Notes",
                tags=["note", "list"],
                icon="📋",
            ),
            Command(
                name="note:delete",
                command_type=CommandType.NOTE,
                description="Delete a note",
                command_template=f"{self.notes_cli_path} delete {{title}}",
                category="Notes",
                tags=["note", "delete"],
                icon="🗑️",
            ),
            Command(
                name="note:recent",
                command_type=CommandType.NOTE,
                description="Show recent notes",
                command_template=f"{self.notes_cli_path} recent",
                category="Notes",
                tags=["note", "recent"],
                icon="🕐",
            ),
        ]

        registry.register_commands(note_commands)

    def create_note(self, title: str, content: Optional[str] = None) -> bool:
        """Create a new note."""
        try:
            cmd = [self.notes_cli_path, "create", title]
            if content:
                cmd.extend(["--content", content])

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def search_notes(self, query: str) -> list[str]:
        """Search for notes."""
        try:
            result = subprocess.run(
                [self.notes_cli_path, "search", query],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
            return []
        except Exception:
            return []

    def list_notes(self) -> list[str]:
        """List all notes."""
        try:
            result = subprocess.run(
                [self.notes_cli_path, "list"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
            return []
        except Exception:
            return []
