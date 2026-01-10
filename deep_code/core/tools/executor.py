"""
Tool Executor with permission integration for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Tool execution with permission checks
- Tool-to-domain mapping
- Dangerous operation detection
- Audit logging
"""

import re
from typing import Any, Callable, Dict, List, Optional

from deep_code.core.tools.base import Tool, ToolResult, ToolPermissionError
from deep_code.core.tools.registry import ToolRegistry, ToolNotFoundError
from deep_code.security.permissions import (
    PermissionManager,
    PermissionDomain,
    PermissionAction,
    PermissionStatus,
    PermissionApprover,
    create_default_manager,
)


# Tool name to permission domain mapping
TOOL_DOMAIN_MAP: Dict[str, PermissionDomain] = {
    "Read": PermissionDomain.FILE_READ,
    "Glob": PermissionDomain.FILE_READ,
    "Grep": PermissionDomain.FILE_READ,
    "Write": PermissionDomain.FILE_WRITE,
    "Edit": PermissionDomain.FILE_WRITE,
    "Bash": PermissionDomain.COMMAND,
}

# Dangerous command patterns
DANGEROUS_COMMAND_PATTERNS = [
    r"^rm\s+",
    r"^rm$",
    r"^rmdir\s+",
    r"^del\s+",
    r"^del$",
    r"^format\s+",
    r"^mkfs\s+",
    r"^dd\s+",
    r"^shutdown",
    r"^reboot",
    r"^halt",
    r"^poweroff",
    r">\s*/dev/sd",
    r">\s*/dev/hd",
    r"chmod\s+777",
    r"chown\s+root",
    r":\(\)\s*\{",  # Fork bomb pattern
]

# Compiled patterns for efficiency
_DANGEROUS_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_COMMAND_PATTERNS]


def get_permission_domain(tool_name: str, arguments: Dict[str, Any]) -> Optional[PermissionDomain]:
    """
    Get the permission domain for a tool.

    Args:
        tool_name: Name of the tool
        arguments: Tool arguments

    Returns:
        PermissionDomain or None if tool doesn't require permission
    """
    return TOOL_DOMAIN_MAP.get(tool_name)


def get_permission_target(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Extract the permission target from tool arguments.

    Args:
        tool_name: Name of the tool
        arguments: Tool arguments

    Returns:
        Target string for permission check
    """
    # File operations
    if "file_path" in arguments:
        return arguments["file_path"]

    # Command operations
    if "command" in arguments:
        return arguments["command"]

    # Pattern-based operations (Glob, Grep)
    if "pattern" in arguments:
        path = arguments.get("path", "")
        pattern = arguments["pattern"]
        if path:
            return f"{path}/{pattern}" if not path.endswith("/") else f"{path}{pattern}"
        return pattern

    # Default
    return "*"


def is_dangerous_operation(tool_name: str, arguments: Dict[str, Any]) -> bool:
    """
    Check if an operation is potentially dangerous.

    Args:
        tool_name: Name of the tool
        arguments: Tool arguments

    Returns:
        True if operation is dangerous
    """
    # Write operations are always considered dangerous
    if tool_name in ("Write", "Edit"):
        return True

    # Check command patterns
    if tool_name == "Bash":
        command = arguments.get("command", "")
        for pattern in _DANGEROUS_PATTERNS:
            if pattern.search(command):
                return True

    return False


class ToolExecutor:
    """
    Executes tools with permission checks.

    Features:
    - Permission checking before execution
    - Approval callback for ASK permissions
    - Audit logging
    - Dangerous operation detection
    """

    def __init__(
        self,
        registry: ToolRegistry,
        permission_manager: Optional[PermissionManager] = None,
        approval_callback: Optional[Callable[[PermissionDomain, str, Optional[str]], bool]] = None,
    ):
        """
        Initialize ToolExecutor.

        Args:
            registry: Tool registry
            permission_manager: Permission manager (creates default if None)
            approval_callback: Callback for ASK permissions
        """
        self._registry = registry
        self._permission_manager = permission_manager or create_default_manager()
        self._approver = PermissionApprover(
            self._permission_manager,
            approval_callback=approval_callback,
        )

    @property
    def registry(self) -> ToolRegistry:
        """Get tool registry."""
        return self._registry

    @property
    def permission_manager(self) -> PermissionManager:
        """Get permission manager."""
        return self._permission_manager

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        skip_permission_check: bool = False,
    ) -> ToolResult:
        """
        Execute a tool with permission checking.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            skip_permission_check: Skip permission check (use with caution)

        Returns:
            ToolResult with execution result or error
        """
        # Get tool from registry
        try:
            tool = self._registry.get(tool_name)
        except ToolNotFoundError:
            return ToolResult.error_result(
                tool_name,
                f"Tool not found: {tool_name}",
            )

        # Check if tool requires permission
        if not skip_permission_check and tool.requires_permission:
            permission_result = self._check_permission(tool_name, arguments)
            if not permission_result:
                target = get_permission_target(tool_name, arguments)
                return ToolResult.error_result(
                    tool_name,
                    f"Permission denied for {tool_name} on target: {target}",
                    metadata={"permission_denied": True},
                )

        # Execute tool
        try:
            return tool.execute(arguments)
        except ToolPermissionError as e:
            return ToolResult.error_result(
                tool_name,
                f"Permission error: {str(e)}",
                metadata={"permission_error": True},
            )
        except Exception as e:
            return ToolResult.error_result(
                tool_name,
                f"Execution error: {str(e)}",
            )

    def _check_permission(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Check permission for tool execution.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            True if permission granted, False otherwise
        """
        domain = get_permission_domain(tool_name, arguments)
        if domain is None:
            # Tool doesn't require permission check
            return True

        target = get_permission_target(tool_name, arguments)
        permission = self._approver.request_permission(domain, target)

        return permission.granted

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """
        Get audit log of permission checks.

        Returns:
            List of audit entries
        """
        return self._approver.get_audit_history()

    def clear_audit_log(self) -> None:
        """Clear audit log."""
        self._approver.clear_audit_log()

    def is_tool_dangerous(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Check if a tool operation is dangerous.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            True if operation is dangerous
        """
        # Check tool's is_dangerous property
        try:
            tool = self._registry.get(tool_name)
            if tool.is_dangerous:
                return True
        except ToolNotFoundError:
            pass

        # Check operation-specific danger
        return is_dangerous_operation(tool_name, arguments)

    def execute_with_confirmation(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        confirm_callback: Callable[[str, str, Dict[str, Any]], bool],
    ) -> ToolResult:
        """
        Execute a tool with explicit confirmation for dangerous operations.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            confirm_callback: Callback for confirmation (tool_name, target, args) -> bool

        Returns:
            ToolResult with execution result or error
        """
        # Check if dangerous
        if self.is_tool_dangerous(tool_name, arguments):
            target = get_permission_target(tool_name, arguments)
            if not confirm_callback(tool_name, target, arguments):
                return ToolResult.error_result(
                    tool_name,
                    "Operation cancelled by user",
                    metadata={"cancelled": True},
                )

        return self.execute(tool_name, arguments)
