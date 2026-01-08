"""
Interaction module for Claude Code

Contains parser, commands, hooks, and prompt-related functionality.
"""

from claude_code.interaction.commands import (
    CommandArgumentError,
    CommandFrontmatter,
    SlashCommand,
    SlashCommandManager,
    create_default_manager,
    execute_command_template,
)

__all__ = [
    "CommandArgumentError",
    "CommandFrontmatter",
    "SlashCommand",
    "SlashCommandManager",
    "create_default_manager",
    "execute_command_template",
]
