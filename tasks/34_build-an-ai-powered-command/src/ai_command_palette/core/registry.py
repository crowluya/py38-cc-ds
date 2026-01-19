"""Command registry and discovery system."""

import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel


class CommandType(Enum):
    """Types of commands."""

    SYSTEM = "system"  # System commands in PATH
    NOTE = "note"  # Note-taking commands
    FILE = "file"  # File operations
    WORKFLOW = "workflow"  # Custom workflows/macros
    ALIAS = "alias"  # Shell aliases


class Command(BaseModel):
    """Representation of a command."""

    name: str
    command_type: CommandType
    description: Optional[str] = None
    command_template: str  # Command with placeholders, e.g., "git commit -m '{msg}'"
    category: Optional[str] = None
    tags: list[str] = []
    icon: Optional[str] = None
    requires_args: bool = False

    def __str__(self) -> str:
        """String representation."""
        return self.name

    def execute(self, **kwargs) -> str:
        """Format command with provided arguments."""
        return self.command_template.format(**kwargs)


class CommandRegistry:
    """Registry for available commands."""

    def __init__(self):
        """Initialize command registry."""
        self._commands: dict[str, Command] = {}
        self._categories: dict[str, list[str]] = {}
        self._file_index: dict[str, Path] = {}

    def register(self, command: Command):
        """Register a new command."""
        self._commands[command.name] = command

        # Add to category
        if command.category:
            if command.category not in self._categories:
                self._categories[command.category] = []
            self._categories[command.category].append(command.name)

        # Add tags
        for tag in command.tags:
            if tag not in self._categories:
                self._categories[tag] = []
            self._categories[tag].append(command.name)

    def register_commands(self, commands: list[Command]):
        """Register multiple commands."""
        for cmd in commands:
            self.register(cmd)

    def get(self, name: str) -> Optional[Command]:
        """Get command by name."""
        return self._commands.get(name)

    def get_all(self) -> list[Command]:
        """Get all registered commands."""
        return list(self._commands.values())

    def get_by_category(self, category: str) -> list[Command]:
        """Get commands by category."""
        names = self._categories.get(category, [])
        return [self._commands[name] for name in names if name in self._commands]

    def get_by_type(self, command_type: CommandType) -> list[Command]:
        """Get commands by type."""
        return [cmd for cmd in self._commands.values() if cmd.command_type == command_type]

    def search(self, query: str) -> list[Command]:
        """Search commands by name, description, or tags."""
        query_lower = query.lower()
        results = []

        for cmd in self._commands.values():
            # Match name
            if query_lower in cmd.name.lower():
                results.append(cmd)
                continue

            # Match description
            if cmd.description and query_lower in cmd.description.lower():
                results.append(cmd)
                continue

            # Match tags
            if any(query_lower in tag.lower() for tag in cmd.tags):
                results.append(cmd)
                continue

            # Match category
            if cmd.category and query_lower in cmd.category.lower():
                results.append(cmd)

        return results

    def discover_system_commands(self) -> list[Command]:
        """Discover available system commands from PATH."""
        commands = []
        seen = set()

        # Get PATH directories
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)

        for dir_path in path_dirs:
            if not Path(dir_path).exists():
                continue

            try:
                for entry in Path(dir_path).iterdir():
                    # Skip if not executable or already seen
                    if entry.name in seen or not entry.is_file():
                        continue

                    # Check if executable
                    if os.access(entry, os.X_OK):
                        seen.add(entry.name)
                        commands.append(
                            Command(
                                name=entry.name,
                                command_type=CommandType.SYSTEM,
                                description=f"System command: {entry.name}",
                                command_template=entry.name,
                                category="System",
                            )
                        )
            except PermissionError:
                continue

        return commands

    def index_files(
        self,
        directory: Optional[Path] = None,
        max_depth: int = 3,
        include_hidden: bool = False,
        extensions: Optional[list[str]] = None,
    ) -> dict[str, Path]:
        """Index files in directory for quick access."""
        if directory is None:
            directory = Path.cwd()

        self._file_index = {}
        extensions_set = set(extensions) if extensions else None

        try:
            for root, dirs, files in os.walk(directory):
                # Calculate depth
                depth = str(Path(root).relative_to(directory)).count(os.sep)

                if depth > max_depth:
                    # Don't go deeper
                    dirs.clear()
                    continue

                # Filter hidden directories
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]

                for filename in files:
                    # Skip hidden files
                    if not include_hidden and filename.startswith("."):
                        continue

                    # Filter by extension
                    if extensions_set:
                        ext = Path(filename).suffix.lower()
                        if ext not in extensions_set:
                            continue

                    file_path = Path(root) / filename
                    rel_path = str(file_path.relative_to(directory))
                    self._file_index[rel_path] = file_path
        except PermissionError:
            pass

        return self._file_index

    def get_files(self) -> list[Command]:
        """Get indexed files as commands."""
        commands = []

        for rel_path, abs_path in self._file_index.items():
            commands.append(
                Command(
                    name=rel_path,
                    command_type=CommandType.FILE,
                    description=f"Open file: {rel_path}",
                    command_template=f'{{{{editor}}}} "{abs_path}"',
                    category="Files",
                )
            )

        return commands

    def load_default_commands(self):
        """Load default command set."""
        # Note-taking commands
        note_commands = [
            Command(
                name="note:create",
                command_type=CommandType.NOTE,
                description="Create a new note",
                command_template="note create {title}",
                category="Notes",
                tags=["note", "create", "new"],
                icon="📝",
            ),
            Command(
                name="note:search",
                command_type=CommandType.NOTE,
                description="Search notes",
                command_template="note search {query}",
                category="Notes",
                tags=["note", "search", "find"],
                icon="🔍",
            ),
            Command(
                name="note:edit",
                command_type=CommandType.NOTE,
                description="Edit a note",
                command_template="note edit {title}",
                category="Notes",
                tags=["note", "edit"],
                icon="✏️",
            ),
            Command(
                name="note:list",
                command_type=CommandType.NOTE,
                description="List all notes",
                command_template="note list",
                category="Notes",
                tags=["note", "list"],
                icon="📋",
            ),
        ]

        # Git commands
        git_commands = [
            Command(
                name="git:status",
                command_type=CommandType.SYSTEM,
                description="Show git status",
                command_template="git status",
                category="Git",
                tags=["git", "status"],
                icon="📊",
            ),
            Command(
                name="git:commit",
                command_type=CommandType.SYSTEM,
                description="Commit changes",
                command_template="git commit -m '{msg}'",
                category="Git",
                tags=["git", "commit"],
                icon="✅",
                requires_args=True,
            ),
            Command(
                name="git:push",
                command_type=CommandType.SYSTEM,
                description="Push to remote",
                command_template="git push",
                category="Git",
                tags=["git", "push"],
                icon="⬆️",
            ),
            Command(
                name="git:pull",
                command_type=CommandType.SYSTEM,
                description="Pull from remote",
                command_template="git pull",
                category="Git",
                tags=["git", "pull"],
                icon="⬇️",
            ),
        ]

        # File operations
        file_commands = [
            Command(
                name="file:find",
                command_type=CommandType.FILE,
                description="Find files by name",
                command_template="find . -name '*{pattern}*' -type f",
                category="Files",
                tags=["file", "find", "search"],
                icon="🔎",
            ),
            Command(
                name="file:grep",
                command_type=CommandType.FILE,
                description="Search file contents",
                command_template="grep -r '{pattern}' .",
                category="Files",
                tags=["file", "grep", "search"],
                icon="🔍",
            ),
        ]

        self.register_commands(note_commands + git_commands + file_commands)

    def initialize(self):
        """Initialize the registry with default commands and system discovery."""
        self.load_default_commands()

        # Auto-discover system commands
        # Note: This can be slow, so we might want to cache this
        # system_commands = self.discover_system_commands()
        # self.register_commands(system_commands)
