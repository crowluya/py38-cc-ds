"""
Core module for Claude Code

Contains core functionality for context management,
execution, and agent operations.
"""

from claude_code.core.agent import (
    Agent,
    AgentConfig,
    CommandOutputContext,
    ConversationTurn,
    Message,
    MessageRole,
    ToolCall,
    ToolResult,
    ToolType,
    add_assistant_message,
    add_user_message,
    create_agent,
    create_history,
    deserialize_history,
    inject_command_output,
    serialize_history,
)
from claude_code.core.context import (
    CircularImportError,
    ContextBuilder,
    ContextFormatter,
    ContextManager,
    DirectoryContext,
    FileContext,
    LoadError,
    LongTermMemory,
    ModularLoader,
    format_directory_context,
    format_file_context,
)
from claude_code.core.executor import CommandExecutor, CommandResult, execute_command

__all__ = [
    # Agent
    "Agent",
    "AgentConfig",
    "CommandOutputContext",
    "ConversationTurn",
    "Message",
    "MessageRole",
    "ToolCall",
    "ToolResult",
    "ToolType",
    "add_assistant_message",
    "add_user_message",
    "create_agent",
    "create_history",
    "deserialize_history",
    "inject_command_output",
    "serialize_history",
    # Context
    "CircularImportError",
    "ContextBuilder",
    "ContextFormatter",
    "ContextManager",
    "DirectoryContext",
    "FileContext",
    "LoadError",
    "LongTermMemory",
    "ModularLoader",
    "format_file_context",
    "format_directory_context",
    # Executor
    "CommandExecutor",
    "CommandResult",
    "execute_command",
]

