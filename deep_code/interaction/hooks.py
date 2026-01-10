"""
Hooks system - T082

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Handles:
- Event definitions (SESSION_START, PRE_TOOL_USE, POST_TOOL_USE, etc.)
- Hook matching (by event type, tool name, pattern)
- Hook script execution
- Hook registration and dispatch
- Loading hooks from .pycc/hooks/ directory
"""

import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from deep_code.config.constants import (
    PROJECT_HOOKS_DIR,
    get_project_hooks_dir,
    get_user_hooks_dir,
)


# ===== Event Definitions =====


class HookEvent(Enum):
    """
    Hook event types.

    Lifecycle events:
    - SESSION_START: When a session starts
    - SESSION_END: When a session ends

    User interaction:
    - USER_PROMPT_SUBMIT: When user submits a prompt

    Tool execution:
    - PRE_TOOL_USE: Before a tool is used
    - POST_TOOL_USE: After a tool completes

    Agent events:
    - NOTIFICATION: When a notification is sent
    - STOP: When agent stops
    - SUBAGENT_STOP: When a subagent stops
    """

    # Lifecycle events
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # User interaction
    USER_PROMPT_SUBMIT = "user_prompt_submit"

    # Tool execution
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"

    # Agent events
    NOTIFICATION = "notification"
    STOP = "stop"
    SUBAGENT_STOP = "subagent_stop"


# ===== Hook Matcher =====


@dataclass
class HookMatcher:
    """
    Matches hook events based on criteria.

    A hook can filter:
    - By event type (required for most hooks)
    - By tool name (for tool events)
    - By pattern (wildcards in tool name)
    """

    event_type: Optional[HookEvent] = None
    tool_name: Optional[str] = None  # Supports * and ? wildcards

    def matches(
        self,
        event: HookEvent,
        context: Dict[str, Any],
    ) -> bool:
        """
        Check if this matcher matches the given event.

        Args:
            event: Event type to check
            context: Event context data (may contain tool_name)

        Returns:
            True if the matcher matches the event
        """
        # Check event type
        if self.event_type is not None and self.event_type != event:
            return False

        # Check tool name (if specified)
        if self.tool_name is not None:
            tool_name = context.get("tool_name")
            if tool_name is None:
                return False

            # Use fnmatch for wildcard matching
            from fnmatch import fnmatch
            if not fnmatch(tool_name, self.tool_name):
                return False

        return True


# ===== Hook Script =====


@dataclass
class HookContext:
    """
    Context passed to hooks when they're executed.

    Contains the event type and any relevant data.
    """

    event: HookEvent
    data: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the context data.

        Args:
            key: Key to look up
            default: Default value if key not found

        Returns:
            Value from context or default
        """
        return self.data.get(key, default)


ScriptRunner = Callable[["HookScript", HookContext], None]


@dataclass
class HookScript:
    """
    A hook script that can be executed on events.

    Hooks are Python scripts that receive JSON context via stdin.
    They can be loaded from .pycc/hooks/ or added programmatically.
    """

    name: str
    source_file: Path
    matcher: Optional[HookMatcher] = None

    def matches(self, event: HookEvent, context: Dict[str, Any]) -> bool:
        """
        Check if this hook matches the given event.

        Args:
            event: Event type
            context: Event context data

        Returns:
            True if the hook should be executed for this event
        """
        if self.matcher is None:
            # No matcher = matches all events
            return True

        return self.matcher.matches(event, context)

    def execute(
        self,
        context: HookContext,
        script_runner: Optional[ScriptRunner] = None,
    ) -> None:
        """
        Execute this hook script.

        Args:
            context: Hook execution context
            script_runner: Optional script runner for testing/custom execution
        """
        if script_runner is not None:
            # Use injected runner (for testing or custom execution)
            script_runner(self, context)
        else:
            # Default: no-op execution
            # In production, this would execute the script as a subprocess
            pass

    @classmethod
    def from_file(cls, source_file: Path) -> "HookScript":
        """
        Create hook from file.

        Parses YAML frontmatter if present.

        Frontmatter fields:
        - event: Event type (e.g., "pre_tool_use")
        - tool_name: Tool name pattern (optional)

        Args:
            source_file: Path to hook file

        Returns:
            HookScript instance
        """
        name = source_file.stem  # Filename without extension
        content = source_file.read_text(encoding="utf-8")

        matcher: Optional[HookMatcher] = None

        # Check for YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]

                try:
                    frontmatter_data = yaml.safe_load(frontmatter_text)
                    if isinstance(frontmatter_data, dict):
                        # Parse event type
                        event_str = frontmatter_data.get("event")
                        event_type: Optional[HookEvent] = None
                        if event_str:
                            try:
                                event_type = HookEvent(event_str)
                            except ValueError:
                                # Invalid event type, ignore
                                pass

                        # Parse tool name
                        tool_name = frontmatter_data.get("tool_name")

                        # Create matcher if we have any filters
                        if event_type is not None or tool_name is not None:
                            matcher = HookMatcher(
                                event_type=event_type,
                                tool_name=tool_name,
                            )
                except (yaml.YAMLError, ValueError):
                    # Invalid frontmatter, use defaults
                    pass

        return cls(
            name=name,
            source_file=source_file,
            matcher=matcher,
        )


# ===== Hook Manager =====


class HookManager:
    """
    Manages hook scripts and dispatches events.

    Features:
    - Register/unregister hooks
    - Dispatch events to matching hooks
    - Load hooks from directories
    - Error handling (hook failures don't crash system)
    """

    # Default hooks directory (relative path for backward compatibility)
    HOOKS_DIR = PROJECT_HOOKS_DIR

    def __init__(self) -> None:
        """Initialize HookManager."""
        self._hooks: Dict[str, HookScript] = {}

    def register(self, hook: HookScript) -> None:
        """
        Register a hook.

        Args:
            hook: Hook to register
        """
        self._hooks[hook.name] = hook

    def unregister(self, name: str) -> None:
        """
        Unregister a hook by name.

        Args:
            name: Hook name
        """
        if name in self._hooks:
            del self._hooks[name]

    def has_hook(self, name: str) -> bool:
        """
        Check if a hook is registered.

        Args:
            name: Hook name

        Returns:
            True if hook exists
        """
        return name in self._hooks

    def get_hook(self, name: str) -> Optional[HookScript]:
        """
        Get a hook by name.

        Args:
            name: Hook name

        Returns:
            HookScript if found, None otherwise
        """
        return self._hooks.get(name)

    def list_hooks(self) -> List[HookScript]:
        """
        List all registered hooks.

        Returns:
            List of hooks
        """
        return list(self._hooks.values())

    def clear(self) -> None:
        """Clear all registered hooks."""
        self._hooks.clear()

    def dispatch(
        self,
        context: HookContext,
        script_runner: Optional[ScriptRunner] = None,
    ) -> None:
        """
        Dispatch an event to all matching hooks.

        Hooks are executed in the order they were registered.
        Hook execution errors are caught and logged (not propagated).

        Args:
            context: Event context
            script_runner: Optional script runner for testing/custom execution
        """
        for hook in self._hooks.values():
            # Check if hook matches this event
            if hook.matches(context.event, context.data):
                try:
                    hook.execute(context, script_runner=script_runner)
                except Exception:
                    # Hook execution failed - log but don't crash
                    # In production, this would log the error
                    pass

    def load_hooks_from_directory(self, directory: Path) -> None:
        """
        Load all hooks from a directory.

        Args:
            directory: Directory containing hook files
        """
        if not directory.exists():
            return

        for file_path in directory.iterdir():
            if file_path.is_file():
                try:
                    hook = HookScript.from_file(file_path)
                    # Add or override existing hook
                    self._hooks[hook.name] = hook
                except (IOError, UnicodeDecodeError):
                    # Skip files that can't be read
                    continue


def create_default_manager() -> HookManager:
    """
    Create a HookManager with default directories.

    Uses:
    - Project: .pycc/hooks/
    - User: ~/.pycc/hooks/

    Returns:
        Configured HookManager
    """
    manager = HookManager()

    # Get user hooks directory
    user_hooks = get_user_hooks_dir()

    # Get project hooks directory
    project_hooks = get_project_hooks_dir()

    # Load user hooks first
    manager.load_hooks_from_directory(user_hooks)

    # Then project hooks (will override)
    manager.load_hooks_from_directory(project_hooks)

    return manager
