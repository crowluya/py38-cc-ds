"""
Tests for Hooks system - T082

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Tests:
- HookEvent enum values
- HookMatcher matching logic
- HookScript execution
- HookManager registration and dispatch
- Error handling
- Loading hooks from directory
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_code.interaction.hooks import (
    HookEvent,
    HookMatcher,
    HookScript,
    HookManager,
    HookContext,
    create_default_manager,
)


class TestHookEvent:
    """Test HookEvent enum."""

    def test_event_values(self) -> None:
        """Test that all expected events exist."""
        # Core lifecycle events
        assert HookEvent.SESSION_START.value == "session_start"
        assert HookEvent.SESSION_END.value == "session_end"

        # User interaction events
        assert HookEvent.USER_PROMPT_SUBMIT.value == "user_prompt_submit"

        # Tool execution events
        assert HookEvent.PRE_TOOL_USE.value == "pre_tool_use"
        assert HookEvent.POST_TOOL_USE.value == "post_tool_use"

        # Agent events
        assert HookEvent.NOTIFICATION.value == "notification"
        assert HookEvent.STOP.value == "stop"
        assert HookEvent.SUBAGENT_STOP.value == "subagent_stop"


class TestHookMatcher:
    """Test HookMatcher."""

    def test_match_by_event_type(self) -> None:
        """Test matching by exact event type."""
        matcher = HookMatcher(event_type=HookEvent.PRE_TOOL_USE)

        assert matcher.matches(HookEvent.PRE_TOOL_USE, {}) is True
        assert matcher.matches(HookEvent.POST_TOOL_USE, {}) is False
        assert matcher.matches(HookEvent.SESSION_START, {}) is False

    def test_match_by_tool_name(self) -> None:
        """Test matching by tool name pattern."""
        # Match specific tool
        matcher = HookMatcher(
            event_type=HookEvent.PRE_TOOL_USE,
            tool_name="str_replace_editor"
        )

        context = {"tool_name": "str_replace_editor"}
        assert matcher.matches(HookEvent.PRE_TOOL_USE, context) is True

        context = {"tool_name": "bash"}
        assert matcher.matches(HookEvent.PRE_TOOL_USE, context) is False

    def test_match_by_pattern(self) -> None:
        """Test matching by wildcard pattern."""
        # Match all tools starting with "str_"
        matcher = HookMatcher(
            event_type=HookEvent.PRE_TOOL_USE,
            tool_name="str_*"
        )

        context = {"tool_name": "str_replace_editor"}
        assert matcher.matches(HookEvent.PRE_TOOL_USE, context) is True

        context = {"tool_name": "str_search"}
        assert matcher.matches(HookEvent.PRE_TOOL_USE, context) is True

        context = {"tool_name": "bash"}
        assert matcher.matches(HookEvent.PRE_TOOL_USE, context) is False

    def test_match_all_events(self) -> None:
        """Test matcher that matches all events."""
        matcher = HookMatcher()  # No filters

        assert matcher.matches(HookEvent.SESSION_START, {}) is True
        assert matcher.matches(HookEvent.PRE_TOOL_USE, {}) is True
        assert matcher.matches(HookEvent.POST_TOOL_USE, {}) is True

    def test_match_without_tool_name(self) -> None:
        """Test matching when context has no tool_name."""
        matcher = HookMatcher(event_type=HookEvent.SESSION_START)

        # SESSION_START doesn't require tool_name
        assert matcher.matches(HookEvent.SESSION_START, {}) is True

        # Tool event without tool_name should not match tool-specific matcher
        tool_matcher = HookMatcher(
            event_type=HookEvent.PRE_TOOL_USE,
            tool_name="bash"
        )
        assert tool_matcher.matches(HookEvent.PRE_TOOL_USE, {}) is False


class FakeScriptRunner:
    """Fake script runner for testing."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []

    def __call__(self, script: HookScript, context: HookContext) -> None:
        """
        Fake run implementation (callable).

        Args:
            script: Hook script to execute
            context: Hook execution context
        """
        self.calls.append((script, context))


class TestHookScript:
    """Test HookScript."""

    def test_script_creation(self) -> None:
        """Test creating a hook script."""
        script = HookScript(
            name="test_hook",
            source_file=Path("/test/script.py"),
        )

        assert script.name == "test_hook"
        assert script.source_file == Path("/test/script.py")

    def test_script_with_matcher(self) -> None:
        """Test creating a hook script with matcher."""
        matcher = HookMatcher(
            event_type=HookEvent.PRE_TOOL_USE,
            tool_name="bash"
        )

        script = HookScript(
            name="bash_hook",
            source_file=Path("/test/bash_hook.py"),
            matcher=matcher,
        )

        assert script.name == "bash_hook"
        assert script.matcher is not None
        assert script.matcher.matches(HookEvent.PRE_TOOL_USE, {"tool_name": "bash"}) is True

    def test_script_matches(self) -> None:
        """Test script matches method."""
        matcher = HookMatcher(
            event_type=HookEvent.POST_TOOL_USE,
            tool_name="str_*"
        )

        script = HookScript(
            name="str_hook",
            source_file=Path("/test/str_hook.py"),
            matcher=matcher,
        )

        # Should match
        assert script.matches(HookEvent.POST_TOOL_USE, {"tool_name": "str_replace"}) is True

        # Should not match (wrong event)
        assert script.matches(HookEvent.PRE_TOOL_USE, {"tool_name": "str_replace"}) is False

        # Should not match (wrong tool pattern)
        assert script.matches(HookEvent.POST_TOOL_USE, {"tool_name": "bash"}) is False

    def test_script_execute(self) -> None:
        """Test script execution."""
        runner = FakeScriptRunner()

        script = HookScript(
            name="test_hook",
            source_file=Path("/test/script.py"),
        )

        context = HookContext(
            event=HookEvent.SESSION_START,
            data={},
        )

        script.execute(context, script_runner=runner)

        assert len(runner.calls) == 1
        assert runner.calls[0] == (script, context)


class TestHookContext:
    """Test HookContext."""

    def test_context_creation(self) -> None:
        """Test creating a hook context."""
        context = HookContext(
            event=HookEvent.PRE_TOOL_USE,
            data={"tool_name": "bash", "command": "ls"},
        )

        assert context.event == HookEvent.PRE_TOOL_USE
        assert context.data == {"tool_name": "bash", "command": "ls"}

    def test_context_get(self) -> None:
        """Test getting values from context."""
        context = HookContext(
            event=HookEvent.POST_TOOL_USE,
            data={"tool_name": "bash", "exit_code": 0},
        )

        assert context.get("tool_name") == "bash"
        assert context.get("exit_code") == 0
        assert context.get("missing_key", "default") == "default"


class TestHookManager:
    """Test HookManager."""

    def test_register_hook(self) -> None:
        """Test registering a hook."""
        manager = HookManager()

        hook = HookScript(
            name="test_hook",
            source_file=Path("/test/script.py"),
        )

        manager.register(hook)

        assert manager.has_hook("test_hook") is True
        assert manager.get_hook("test_hook") == hook

    def test_register_multiple_hooks(self) -> None:
        """Test registering multiple hooks."""
        manager = HookManager()

        hook1 = HookScript(name="hook1", source_file=Path("/test/hook1.py"))
        hook2 = HookScript(name="hook2", source_file=Path("/test/hook2.py"))

        manager.register(hook1)
        manager.register(hook2)

        assert manager.has_hook("hook1") is True
        assert manager.has_hook("hook2") is True

    def test_unregister_hook(self) -> None:
        """Test unregistering a hook."""
        manager = HookManager()

        hook = HookScript(name="test_hook", source_file=Path("/test/script.py"))
        manager.register(hook)

        assert manager.has_hook("test_hook") is True

        manager.unregister("test_hook")

        assert manager.has_hook("test_hook") is False
        assert manager.get_hook("test_hook") is None

    def test_dispatch_event(self) -> None:
        """Test dispatching event to matching hooks."""
        manager = HookManager()
        runner = FakeScriptRunner()

        # Register hooks for different events
        hook1 = HookScript(
            name="session_hook",
            source_file=Path("/test/session.py"),
            matcher=HookMatcher(event_type=HookEvent.SESSION_START),
        )

        hook2 = HookScript(
            name="tool_hook",
            source_file=Path("/test/tool.py"),
            matcher=HookMatcher(event_type=HookEvent.PRE_TOOL_USE),
        )

        manager.register(hook1)
        manager.register(hook2)

        # Dispatch SESSION_START - should only trigger hook1
        context = HookContext(event=HookEvent.SESSION_START, data={})
        manager.dispatch(context, script_runner=runner)

        assert len(runner.calls) == 1
        assert runner.calls[0][0] == hook1

    def test_dispatch_with_tool_matching(self) -> None:
        """Test dispatching with tool name matching."""
        manager = HookManager()
        runner = FakeScriptRunner()

        # Register hook for bash tools only
        hook = HookScript(
            name="bash_hook",
            source_file=Path("/test/bash.py"),
            matcher=HookMatcher(
                event_type=HookEvent.PRE_TOOL_USE,
                tool_name="bash"
            ),
        )

        manager.register(hook)

        # Dispatch with bash tool - should match
        context = HookContext(
            event=HookEvent.PRE_TOOL_USE,
            data={"tool_name": "bash"}
        )
        manager.dispatch(context, script_runner=runner)

        assert len(runner.calls) == 1

        # Dispatch with different tool - should not match
        runner.calls.clear()
        context = HookContext(
            event=HookEvent.PRE_TOOL_USE,
            data={"tool_name": "str_replace_editor"}
        )
        manager.dispatch(context, script_runner=runner)

        assert len(runner.calls) == 0

    def test_dispatch_with_pattern_matching(self) -> None:
        """Test dispatching with wildcard patterns."""
        manager = HookManager()
        runner = FakeScriptRunner()

        # Register hook for all str_* tools
        hook = HookScript(
            name="str_hook",
            source_file=Path("/test/str.py"),
            matcher=HookMatcher(
                event_type=HookEvent.PRE_TOOL_USE,
                tool_name="str_*"
            ),
        )

        manager.register(hook)

        # Should match str_replace_editor
        context = HookContext(
            event=HookEvent.PRE_TOOL_USE,
            data={"tool_name": "str_replace_editor"}
        )
        manager.dispatch(context, script_runner=runner)

        assert len(runner.calls) == 1

        # Should match str_search
        runner.calls.clear()
        context = HookContext(
            event=HookEvent.PRE_TOOL_USE,
            data={"tool_name": "str_search"}
        )
        manager.dispatch(context, script_runner=runner)

        assert len(runner.calls) == 1

        # Should not match bash
        runner.calls.clear()
        context = HookContext(
            event=HookEvent.PRE_TOOL_USE,
            data={"tool_name": "bash"}
        )
        manager.dispatch(context, script_runner=runner)

        assert len(runner.calls) == 0

    def test_dispatch_to_multiple_hooks(self) -> None:
        """Test dispatching to multiple matching hooks."""
        manager = HookManager()
        runner = FakeScriptRunner()

        # Register multiple hooks for same event
        hook1 = HookScript(
            name="hook1",
            source_file=Path("/test/hook1.py"),
            matcher=HookMatcher(event_type=HookEvent.SESSION_START),
        )

        hook2 = HookScript(
            name="hook2",
            source_file=Path("/test/hook2.py"),
            matcher=HookMatcher(event_type=HookEvent.SESSION_START),
        )

        hook3 = HookScript(
            name="hook3",
            source_file=Path("/test/hook3.py"),
            matcher=HookMatcher(event_type=HookEvent.PRE_TOOL_USE),
        )

        manager.register(hook1)
        manager.register(hook2)
        manager.register(hook3)

        # Dispatch SESSION_START - should trigger hook1 and hook2
        context = HookContext(event=HookEvent.SESSION_START, data={})
        manager.dispatch(context, script_runner=runner)

        assert len(runner.calls) == 2
        executed_hooks = {call[0].name for call in runner.calls}
        assert executed_hooks == {"hook1", "hook2"}

    def test_dispatch_without_runner(self) -> None:
        """Test dispatching without script runner (no-op)."""
        manager = HookManager()

        hook = HookScript(
            name="test_hook",
            source_file=Path("/test/script.py"),
            matcher=HookMatcher(event_type=HookEvent.SESSION_START),
        )

        manager.register(hook)

        # Should not raise any error
        context = HookContext(event=HookEvent.SESSION_START, data={})
        manager.dispatch(context)  # No script_runner

    def test_list_hooks(self) -> None:
        """Test listing all registered hooks."""
        manager = HookManager()

        hook1 = HookScript(name="hook1", source_file=Path("/test/hook1.py"))
        hook2 = HookScript(name="hook2", source_file=Path("/test/hook2.py"))

        manager.register(hook1)
        manager.register(hook2)

        hooks = manager.list_hooks()
        assert len(hooks) == 2
        assert hook1 in hooks
        assert hook2 in hooks

    def test_clear_hooks(self) -> None:
        """Test clearing all hooks."""
        manager = HookManager()

        hook1 = HookScript(name="hook1", source_file=Path("/test/hook1.py"))
        hook2 = HookScript(name="hook2", source_file=Path("/test/hook2.py"))

        manager.register(hook1)
        manager.register(hook2)

        assert len(manager.list_hooks()) == 2

        manager.clear()

        assert len(manager.list_hooks()) == 0


class TestHookManagerLoadHooks:
    """Test HookManager loading hooks from directory."""

    def test_load_hooks_from_directory(self) -> None:
        """Test loading hooks from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / "hooks"
            hooks_dir.mkdir()

            # Create a simple hook script
            hook_file = hooks_dir / "session_start.py"
            hook_file.write_text("# Session start hook\n", encoding="utf-8")

            manager = HookManager()
            manager.load_hooks_from_directory(hooks_dir)

            # Should have loaded the hook
            assert manager.has_hook("session_start")
            hook = manager.get_hook("session_start")
            assert hook is not None
            assert hook.name == "session_start"
            assert hook.source_file == hook_file

    def test_load_hooks_with_frontmatter(self) -> None:
        """Test loading hooks with YAML frontmatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / "hooks"
            hooks_dir.mkdir()

            # Create hook with frontmatter
            hook_file = hooks_dir / "bash_hook.py"
            hook_content = """---
event: pre_tool_use
tool_name: bash
---
# Bash hook
"""
            hook_file.write_text(hook_content, encoding="utf-8")

            manager = HookManager()
            manager.load_hooks_from_directory(hooks_dir)

            hook = manager.get_hook("bash_hook")
            assert hook is not None
            assert hook.matcher is not None
            assert hook.matcher.matches(
                HookEvent.PRE_TOOL_USE,
                {"tool_name": "bash"}
            ) is True

    def test_load_hooks_skips_non_files(self) -> None:
        """Test that loading skips subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / "hooks"
            hooks_dir.mkdir()

            # Create a subdirectory
            (hooks_dir / "subdir").mkdir()

            # Create a valid hook
            hook_file = hooks_dir / "valid_hook.py"
            hook_file.write_text("# Valid hook\n", encoding="utf-8")

            manager = HookManager()
            manager.load_hooks_from_directory(hooks_dir)

            # Should only load the file, not the directory
            assert manager.has_hook("valid_hook")
            assert not manager.has_hook("subdir")

    def test_load_hooks_from_nonexistent_directory(self) -> None:
        """Test loading from nonexistent directory (no-op)."""
        manager = HookManager()

        # Should not raise error
        manager.load_hooks_from_directory(Path("/nonexistent/hooks"))

        assert len(manager.list_hooks()) == 0

    def test_load_hooks_overwrites_existing(self) -> None:
        """Test that reloading hooks overwrites existing ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / "hooks"
            hooks_dir.mkdir()

            # Create initial hook
            hook_file = hooks_dir / "test_hook.py"
            hook_file.write_text("# Initial hook\n", encoding="utf-8")

            manager = HookManager()
            manager.load_hooks_from_directory(hooks_dir)

            assert manager.has_hook("test_hook")

            # Update the hook
            hook_file.write_text("# Updated hook\n", encoding="utf-8")

            # Reload
            manager.load_hooks_from_directory(hooks_dir)

            # Should still have the hook (updated)
            assert manager.has_hook("test_hook")


class TestHookManagerErrorHandling:
    """Test error handling in HookManager."""

    def test_hook_execution_error_does_not_crash(self) -> None:
        """Test that hook execution errors don't crash the system."""
        manager = HookManager()

        def failing_runner(script: HookScript, context: HookContext) -> None:
            """Runner that always raises an error."""
            raise RuntimeError("Hook execution failed!")

        hook = HookScript(
            name="failing_hook",
            source_file=Path("/test/failing.py"),
            matcher=HookMatcher(event_type=HookEvent.SESSION_START),
        )

        manager.register(hook)

        # Dispatch with failing runner - should not raise
        context = HookContext(event=HookEvent.SESSION_START, data={})
        manager.dispatch(context, script_runner=failing_runner)

        # System should continue working
        assert manager.has_hook("failing_hook")


class TestCreateDefaultManager:
    """Test create_default_manager function."""

    def test_create_default_manager(self) -> None:
        """Test creating default hook manager."""
        manager = create_default_manager()

        assert isinstance(manager, HookManager)

        # Should load hooks from default directories
        # (Note: may not find any hooks in test environment)
