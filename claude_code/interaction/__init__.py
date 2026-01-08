"""
Interaction module for Claude Code

Contains parser, commands, hooks, and prompt-related functionality.
"""

from claude_code.interaction.commands import (
    CommandArgumentError,
    CommandFrontmatter,
    SlashCommand,
    SlashCommandManager,
    create_default_manager as create_default_command_manager,
    execute_command_template,
)

from claude_code.interaction.hooks import (
    HookContext,
    HookEvent,
    HookManager,
    HookMatcher,
    HookScript,
    ScriptRunner,
    create_default_manager,
)

__all__ = [
    "CommandArgumentError",
    "CommandFrontmatter",
    "SlashCommand",
    "SlashCommandManager",
    "create_default_command_manager",
    "execute_command_template",
    "HookContext",
    "HookEvent",
    "HookManager",
    "HookMatcher",
    "HookScript",
    "ScriptRunner",
    "create_default_manager",
]
