"""
Tests for tool permissions integration (T016)

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict, Optional
from unittest.mock import Mock, MagicMock, patch

from deep_code.core.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolResult,
    ToolPermissionError,
)
from deep_code.core.tools.registry import ToolRegistry
from deep_code.security.permissions import (
    PermissionManager,
    PermissionRule,
    PermissionAction,
    PermissionDomain,
    PermissionStatus,
    PermissionApprover,
)


# Test fixtures

class MockReadTool(Tool):
    """Mock read tool for testing."""

    @property
    def name(self) -> str:
        return "Read"

    @property
    def description(self) -> str:
        return "Read a file"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self):
        return [
            ToolParameter(name="file_path", type="string", description="Path to file")
        ]

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return False

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult.success_result(self.name, f"Content of {arguments.get('file_path')}")


class MockWriteTool(Tool):
    """Mock write tool for testing."""

    @property
    def name(self) -> str:
        return "Write"

    @property
    def description(self) -> str:
        return "Write a file"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters(self):
        return [
            ToolParameter(name="file_path", type="string", description="Path to file"),
            ToolParameter(name="content", type="string", description="Content to write"),
        ]

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return True

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult.success_result(self.name, f"Wrote to {arguments.get('file_path')}")


class MockBashTool(Tool):
    """Mock bash tool for testing."""

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def description(self) -> str:
        return "Execute bash command"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SHELL

    @property
    def parameters(self):
        return [
            ToolParameter(name="command", type="string", description="Command to execute")
        ]

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return True

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult.success_result(self.name, f"Executed: {arguments.get('command')}")


class MockNoPermissionTool(Tool):
    """Mock tool that doesn't require permission."""

    @property
    def name(self) -> str:
        return "TodoWrite"

    @property
    def description(self) -> str:
        return "Write todo list"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def requires_permission(self) -> bool:
        return False

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult.success_result(self.name, "Todo updated")


class TestToolExecutor:
    """Tests for ToolExecutor with permission integration."""

    def test_executor_initialization(self):
        """Test executor initialization."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        assert executor.registry is registry
        assert executor.permission_manager is not None

    def test_executor_with_custom_permission_manager(self):
        """Test executor with custom permission manager."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        perm_manager = PermissionManager()
        executor = ToolExecutor(registry, permission_manager=perm_manager)

        assert executor.permission_manager is perm_manager

    def test_execute_tool_without_permission_requirement(self):
        """Test executing tool that doesn't require permission."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockNoPermissionTool())

        executor = ToolExecutor(registry)
        result = executor.execute("TodoWrite", {"todos": []})

        assert result.success is True

    def test_execute_tool_permission_granted(self):
        """Test executing tool with permission granted."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockReadTool())

        perm_manager = PermissionManager()
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.ALLOW,
            pattern="*",
        ))

        executor = ToolExecutor(registry, permission_manager=perm_manager)
        result = executor.execute("Read", {"file_path": "/tmp/test.txt"})

        assert result.success is True

    def test_execute_tool_permission_denied(self):
        """Test executing tool with permission denied."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockReadTool())

        perm_manager = PermissionManager()
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.DENY,
            pattern="*",
        ))

        executor = ToolExecutor(registry, permission_manager=perm_manager)
        result = executor.execute("Read", {"file_path": "/tmp/test.txt"})

        assert result.success is False
        assert "permission" in result.error.lower() or "denied" in result.error.lower()

    def test_execute_tool_permission_ask_with_callback(self):
        """Test executing tool with ASK permission and approval callback."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockReadTool())

        perm_manager = PermissionManager()
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.ASK,
            pattern="*",
        ))

        # Approval callback that always approves
        def approve_callback(domain, target, reason):
            return True

        executor = ToolExecutor(
            registry,
            permission_manager=perm_manager,
            approval_callback=approve_callback,
        )
        result = executor.execute("Read", {"file_path": "/tmp/test.txt"})

        assert result.success is True

    def test_execute_tool_permission_ask_denied_by_callback(self):
        """Test executing tool with ASK permission denied by callback."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockReadTool())

        perm_manager = PermissionManager()
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.ASK,
            pattern="*",
        ))

        # Approval callback that always denies
        def deny_callback(domain, target, reason):
            return False

        executor = ToolExecutor(
            registry,
            permission_manager=perm_manager,
            approval_callback=deny_callback,
        )
        result = executor.execute("Read", {"file_path": "/tmp/test.txt"})

        assert result.success is False

    def test_execute_tool_not_found(self):
        """Test executing non-existent tool."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = executor.execute("NonExistent", {})

        assert result.success is False
        assert "not found" in result.error.lower()


class TestToolExecutorDomainMapping:
    """Tests for tool-to-permission-domain mapping."""

    def test_read_tool_maps_to_file_read(self):
        """Test Read tool maps to FILE_READ domain."""
        from deep_code.core.tools.executor import ToolExecutor, get_permission_domain

        domain = get_permission_domain("Read", {"file_path": "/tmp/test.txt"})
        assert domain == PermissionDomain.FILE_READ

    def test_write_tool_maps_to_file_write(self):
        """Test Write tool maps to FILE_WRITE domain."""
        from deep_code.core.tools.executor import get_permission_domain

        domain = get_permission_domain("Write", {"file_path": "/tmp/test.txt"})
        assert domain == PermissionDomain.FILE_WRITE

    def test_edit_tool_maps_to_file_write(self):
        """Test Edit tool maps to FILE_WRITE domain."""
        from deep_code.core.tools.executor import get_permission_domain

        domain = get_permission_domain("Edit", {"file_path": "/tmp/test.txt"})
        assert domain == PermissionDomain.FILE_WRITE

    def test_bash_tool_maps_to_command(self):
        """Test Bash tool maps to COMMAND domain."""
        from deep_code.core.tools.executor import get_permission_domain

        domain = get_permission_domain("Bash", {"command": "ls -la"})
        assert domain == PermissionDomain.COMMAND

    def test_glob_tool_maps_to_file_read(self):
        """Test Glob tool maps to FILE_READ domain."""
        from deep_code.core.tools.executor import get_permission_domain

        domain = get_permission_domain("Glob", {"pattern": "*.py"})
        assert domain == PermissionDomain.FILE_READ

    def test_grep_tool_maps_to_file_read(self):
        """Test Grep tool maps to FILE_READ domain."""
        from deep_code.core.tools.executor import get_permission_domain

        domain = get_permission_domain("Grep", {"pattern": "test"})
        assert domain == PermissionDomain.FILE_READ

    def test_unknown_tool_returns_none(self):
        """Test unknown tool returns None domain."""
        from deep_code.core.tools.executor import get_permission_domain

        domain = get_permission_domain("UnknownTool", {})
        assert domain is None


class TestToolExecutorTargetExtraction:
    """Tests for extracting permission target from tool arguments."""

    def test_extract_target_file_path(self):
        """Test extracting file_path as target."""
        from deep_code.core.tools.executor import get_permission_target

        target = get_permission_target("Read", {"file_path": "/tmp/test.txt"})
        assert target == "/tmp/test.txt"

    def test_extract_target_command(self):
        """Test extracting command as target."""
        from deep_code.core.tools.executor import get_permission_target

        target = get_permission_target("Bash", {"command": "ls -la"})
        assert target == "ls -la"

    def test_extract_target_pattern(self):
        """Test extracting pattern as target."""
        from deep_code.core.tools.executor import get_permission_target

        target = get_permission_target("Glob", {"pattern": "*.py", "path": "/src"})
        assert target == "/src/*.py" or target == "*.py"

    def test_extract_target_default(self):
        """Test default target when no specific field found."""
        from deep_code.core.tools.executor import get_permission_target

        target = get_permission_target("Unknown", {"foo": "bar"})
        assert target == "*"


class TestToolExecutorAllowDenyRules:
    """Tests for tool-level allow/deny rules."""

    def test_allow_specific_file(self):
        """Test allowing specific file access."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockReadTool())

        perm_manager = PermissionManager()
        # Deny all by default
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.DENY,
            pattern="*",
        ))
        # Allow specific file
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.ALLOW,
            pattern="/allowed/*.txt",
            priority=10,
        ))

        executor = ToolExecutor(registry, permission_manager=perm_manager)

        # Allowed file
        result = executor.execute("Read", {"file_path": "/allowed/test.txt"})
        assert result.success is True

        # Denied file
        result = executor.execute("Read", {"file_path": "/denied/test.txt"})
        assert result.success is False

    def test_deny_dangerous_commands(self):
        """Test denying dangerous commands."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockBashTool())

        perm_manager = PermissionManager()
        # Allow all commands by default
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.COMMAND,
            action=PermissionAction.ALLOW,
            pattern="*",
        ))
        # Deny rm commands
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.COMMAND,
            action=PermissionAction.DENY,
            pattern="rm *",
            priority=10,
        ))

        executor = ToolExecutor(registry, permission_manager=perm_manager)

        # Safe command
        result = executor.execute("Bash", {"command": "ls -la"})
        assert result.success is True

        # Dangerous command
        result = executor.execute("Bash", {"command": "rm -rf /"})
        assert result.success is False


class TestToolExecutorDangerousOperations:
    """Tests for dangerous operation handling."""

    def test_dangerous_tool_requires_confirmation(self):
        """Test that dangerous tools require confirmation."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockWriteTool())

        perm_manager = PermissionManager()
        # ASK for all file writes
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_WRITE,
            action=PermissionAction.ASK,
            pattern="*",
        ))

        confirmation_requested = []

        def track_callback(domain, target, reason):
            confirmation_requested.append((domain, target))
            return True

        executor = ToolExecutor(
            registry,
            permission_manager=perm_manager,
            approval_callback=track_callback,
        )

        result = executor.execute("Write", {"file_path": "/tmp/test.txt", "content": "test"})

        assert result.success is True
        assert len(confirmation_requested) == 1
        assert confirmation_requested[0][0] == PermissionDomain.FILE_WRITE

    def test_is_dangerous_operation(self):
        """Test checking if operation is dangerous."""
        from deep_code.core.tools.executor import is_dangerous_operation

        # Dangerous commands
        assert is_dangerous_operation("Bash", {"command": "rm -rf /"}) is True
        assert is_dangerous_operation("Bash", {"command": "del /f /q *"}) is True
        assert is_dangerous_operation("Bash", {"command": "format c:"}) is True

        # Safe commands
        assert is_dangerous_operation("Bash", {"command": "ls -la"}) is False
        assert is_dangerous_operation("Bash", {"command": "git status"}) is False

        # Write operations are dangerous
        assert is_dangerous_operation("Write", {"file_path": "/etc/passwd"}) is True

        # Read operations are not dangerous
        assert is_dangerous_operation("Read", {"file_path": "/etc/passwd"}) is False


class TestToolExecutorAuditLog:
    """Tests for audit logging."""

    def test_audit_log_records_executions(self):
        """Test that executions are recorded in audit log."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockReadTool())

        perm_manager = PermissionManager()
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.ALLOW,
            pattern="*",
        ))

        executor = ToolExecutor(registry, permission_manager=perm_manager)
        executor.execute("Read", {"file_path": "/tmp/test.txt"})

        audit_log = executor.get_audit_log()
        assert len(audit_log) == 1
        assert audit_log[0]["target"] == "/tmp/test.txt"
        assert audit_log[0]["granted"] is True

    def test_audit_log_records_denials(self):
        """Test that denials are recorded in audit log."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockReadTool())

        perm_manager = PermissionManager()
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.DENY,
            pattern="*",
        ))

        executor = ToolExecutor(registry, permission_manager=perm_manager)
        executor.execute("Read", {"file_path": "/tmp/secret.txt"})

        audit_log = executor.get_audit_log()
        assert len(audit_log) == 1
        assert audit_log[0]["granted"] is False


class TestToolExecutorIntegration:
    """Integration tests for tool executor."""

    def test_full_workflow(self):
        """Test full workflow with multiple tools and permissions."""
        from deep_code.core.tools.executor import ToolExecutor

        registry = ToolRegistry()
        registry.register(MockReadTool())
        registry.register(MockWriteTool())
        registry.register(MockBashTool())
        registry.register(MockNoPermissionTool())

        perm_manager = PermissionManager()
        # Allow reads
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_READ,
            action=PermissionAction.ALLOW,
            pattern="*",
        ))
        # ASK for writes
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.FILE_WRITE,
            action=PermissionAction.ASK,
            pattern="*",
        ))
        # Allow safe commands
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.COMMAND,
            action=PermissionAction.ALLOW,
            pattern="ls *",
        ))
        perm_manager.add_rule(PermissionRule(
            domain=PermissionDomain.COMMAND,
            action=PermissionAction.DENY,
            pattern="*",
        ))

        def approve_writes(domain, target, reason):
            return target.endswith(".txt")

        executor = ToolExecutor(
            registry,
            permission_manager=perm_manager,
            approval_callback=approve_writes,
        )

        # Read should work
        result = executor.execute("Read", {"file_path": "/tmp/test.txt"})
        assert result.success is True

        # Write to .txt should work (approved)
        result = executor.execute("Write", {"file_path": "/tmp/test.txt", "content": "test"})
        assert result.success is True

        # Write to .py should fail (not approved)
        result = executor.execute("Write", {"file_path": "/tmp/test.py", "content": "test"})
        assert result.success is False

        # ls command should work
        result = executor.execute("Bash", {"command": "ls -la"})
        assert result.success is True

        # rm command should fail
        result = executor.execute("Bash", {"command": "rm -rf /"})
        assert result.success is False

        # TodoWrite doesn't need permission
        result = executor.execute("TodoWrite", {})
        assert result.success is True
