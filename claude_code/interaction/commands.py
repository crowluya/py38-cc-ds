"""
Slash Commands - T080-T081

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Handles:
- Custom slash commands discovery
- Project-level and user-level command directories
- Frontmatter parsing (description, model, allowed_tools)
- Parameter replacement ($1, $2, ..., $ALL_ARGUMENTS)
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from claude_code.config.constants import (
    COMMANDS_DIR,
    PROJECT_COMMANDS_DIR,
    get_user_commands_dir,
)


class CommandArgumentError(Exception):
    """Error in command arguments."""

    pass


@dataclass
class CommandFrontmatter:
    """
    Frontmatter metadata for slash commands.

    Attributes:
        description: Human-readable description
        model: LLM model to use
        allowed_tools: List of tools the command can use
    """

    description: Optional[str] = None
    model: Optional[str] = None
    allowed_tools: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandFrontmatter":
        """
        Create from dictionary.

        Args:
            data: Dictionary from YAML frontmatter

        Returns:
            CommandFrontmatter instance
        """
        return cls(
            description=data.get("description"),
            model=data.get("model"),
            allowed_tools=data.get("allowed_tools", []),
        )


@dataclass
class SlashCommand:
    """
    A custom slash command.

    Commands are stored as text files in `.my-claude/commands/` or `~/.my-claude/commands/`.
    Each file contains a template with optional YAML frontmatter.
    """

    name: str
    template: str
    source_file: Path
    frontmatter: Optional[CommandFrontmatter] = None

    @property
    def description(self) -> Optional[str]:
        """Get command description."""
        if self.frontmatter and self.frontmatter.description:
            return self.frontmatter.description
        # Fallback to first line of template
        lines = self.template.strip().split("\n")
        if lines:
            return lines[0]
        return None

    def display_name(self) -> str:
        """Get display name (with / prefix)."""
        return f"/{self.name}"

    def is_available(self) -> bool:
        """Check if command source file still exists."""
        return self.source_file.exists()

    def execute(self, arguments: Optional[List[str]] = None) -> str:
        """
        Execute the command with arguments.

        Args:
            arguments: List of argument strings

        Returns:
            Rendered template with arguments substituted
        """
        if arguments is None:
            arguments = []

        return execute_command_template(
            template=self.template,
            arguments=arguments,
        )

    @classmethod
    def from_content(
        cls,
        name: str,
        content: str,
        source_file: Path,
    ) -> "SlashCommand":
        """
        Create command from file content.

        Parses YAML frontmatter if present.

        Args:
            name: Command name
            content: File content
            source_file: Source file path

        Returns:
            SlashCommand instance
        """
        frontmatter: Optional[CommandFrontmatter] = None
        template = content

        # Check for YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]
                template = parts[2].lstrip("\n")

                try:
                    frontmatter_data = yaml.safe_load(frontmatter_text)
                    if isinstance(frontmatter_data, dict):
                        frontmatter = CommandFrontmatter.from_dict(frontmatter_data)
                except (yaml.YAMLError, ValueError):
                    # Invalid frontmatter, use defaults
                    frontmatter = None

        return cls(
            name=name,
            template=template,
            source_file=source_file,
            frontmatter=frontmatter,
        )

    @classmethod
    def from_file(cls, source_file: Path) -> "SlashCommand":
        """
        Create command from file.

        Args:
            source_file: Path to command file

        Returns:
            SlashCommand instance
        """
        name = source_file.stem  # Filename without extension
        content = source_file.read_text(encoding="utf-8")

        return cls.from_content(
            name=name,
            content=content,
            source_file=source_file,
        )


def execute_command_template(
    template: str,
    arguments: List[str],
) -> str:
    """
    Execute a command template with argument substitution.

    Placeholders:
    - $1, $2, ..., $n: Positional arguments
    - $ALL_ARGUMENTS: All arguments joined by spaces

    Args:
        template: Command template string
        arguments: List of argument values

    Returns:
        Rendered template
    """
    result = template

    # Replace $ALL_ARGUMENTS first
    all_args = " ".join(arguments)
    result = result.replace("$ALL_ARGUMENTS", all_args)

    # Replace positional arguments
    for i, arg in enumerate(arguments, start=1):
        placeholder = f"${i}"
        result = result.replace(placeholder, arg)

    # Replace any remaining positional placeholders with empty string
    # (for cases where not enough arguments provided)
    import re
    result = re.sub(r"\$\d+", "", result)

    return result


class SlashCommandManager:
    """
    Manages custom slash commands.

    Features:
    - Scan project and user command directories
    - Project commands override user commands
    - Command lookup by name
    - Command execution
    """

    def __init__(self) -> None:
        """Initialize SlashCommandManager."""
        self._commands: Dict[str, SlashCommand] = {}

    def scan_commands(
        self,
        project_dir: Optional[Path] = None,
        user_dir: Optional[Path] = None,
    ) -> None:
        """
        Scan and load commands from directories.

        Project commands take precedence over user commands.

        Args:
            project_dir: Project directory (contains .my-claude/commands/)
            user_dir: User directory (contains commands/)
        """
        # First load user commands
        if user_dir:
            self._load_from_directory(user_dir)

        # Then project commands (will override)
        if project_dir:
            project_commands = project_dir / PROJECT_COMMANDS_DIR
            if project_commands.exists():
                self._load_from_directory(project_commands)

    def _load_from_directory(self, directory: Path) -> None:
        """
        Load all commands from a directory.

        Args:
            directory: Directory containing command files
        """
        if not directory.exists():
            return

        for file_path in directory.iterdir():
            if file_path.is_file():
                # Only read text files
                try:
                    command = SlashCommand.from_file(file_path)
                    # Add or override existing command
                    self._commands[command.name] = command
                except (IOError, UnicodeDecodeError):
                    # Skip files that can't be read
                    continue

    def get_command(self, name: str) -> Optional[SlashCommand]:
        """
        Get a command by name.

        Args:
            name: Command name (without / prefix)

        Returns:
            SlashCommand if found, None otherwise
        """
        return self._commands.get(name)

    def list_commands(self) -> List[str]:
        """
        List all available command names.

        Returns:
            List of command names
        """
        return sorted(self._commands.keys())

    def execute(
        self,
        name: str,
        arguments: Optional[List[str]] = None,
    ) -> str:
        """
        Execute a command.

        Args:
            name: Command name
            arguments: Command arguments

        Returns:
            Rendered command output

        Raises:
            CommandArgumentError: If command not found
        """
        command = self.get_command(name)

        if command is None:
            raise CommandArgumentError(f"Command not found: /{name}")

        return command.execute(arguments)

    def reload(
        self,
        project_dir: Optional[Path] = None,
        user_dir: Optional[Path] = None,
    ) -> None:
        """
        Reload commands from directories.

        Args:
            project_dir: Project directory
            user_dir: User directory
        """
        self._commands.clear()
        self.scan_commands(project_dir=project_dir, user_dir=user_dir)

    def add_command(self, command: SlashCommand) -> None:
        """
        Add a command programmatically.

        Args:
            command: Command to add
        """
        self._commands[command.name] = command

    def remove_command(self, name: str) -> bool:
        """
        Remove a command.

        Args:
            name: Command name

        Returns:
            True if command was removed, False if not found
        """
        if name in self._commands:
            del self._commands[name]
            return True
        return False


def create_default_manager() -> SlashCommandManager:
    """
    Create a SlashCommandManager with default directories.

    Uses:
    - Project: .my-claude/commands/
    - User: ~/.my-claude/commands/

    Returns:
        Configured SlashCommandManager
    """
    manager = SlashCommandManager()

    # Get current directory for project commands
    project_dir = Path.cwd()

    # Get user commands directory from constants
    user_commands = get_user_commands_dir()

    manager.scan_commands(project_dir=project_dir, user_dir=user_commands)

    return manager
