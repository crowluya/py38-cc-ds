"""
Core module for Claude Code

Contains core functionality for context management,
execution, agent operations, and SDD (Spec-Driven Development).
"""

from deep_code.core.agent import (
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
from deep_code.core.context import (
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
from deep_code.core.executor import CommandExecutor, CommandResult, execute_command
from deep_code.core.sdd import (
    CircularDependencyError,
    ExecutorStatus,
    Task,
    TaskExecutionError,
    TaskExecutor,
    TaskExecutorConfig,
    TaskResult,
    TaskStatus,
    analyze_dependencies,
    execute_task,
    group_parallel_tasks,
    parse_tasks_from_markdown,
    topological_sort,
)

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
    # SDD
    "Task",
    "TaskStatus",
    "TaskResult",
    "TaskExecutor",
    "TaskExecutorConfig",
    "ExecutorStatus",
    "TaskExecutionError",
    "CircularDependencyError",
    "parse_tasks_from_markdown",
    "analyze_dependencies",
    "topological_sort",
    "group_parallel_tasks",
    "execute_task",
]

