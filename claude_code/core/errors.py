"""
Unified error handling for Claude Code Python MVP

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Unified error codes
- Structured error class
- Error formatting
- Recovery suggestions
- Exception wrapping
"""

import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from claude_code.core.tools.base import ToolResult


class ErrorCode(Enum):
    """Unified error codes for all tools."""

    # Tool errors
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_DISABLED = "TOOL_DISABLED"

    # Permission errors
    PERMISSION_DENIED = "PERMISSION_DENIED"
    PERMISSION_PENDING = "PERMISSION_PENDING"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    MISSING_ARGUMENT = "MISSING_ARGUMENT"

    # Execution errors
    EXECUTION_ERROR = "EXECUTION_ERROR"
    COMMAND_FAILED = "COMMAND_FAILED"
    TIMEOUT = "TIMEOUT"

    # File errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_ACCESS_ERROR = "FILE_ACCESS_ERROR"
    FILE_EXISTS = "FILE_EXISTS"
    DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"

    # Network errors
    NETWORK_ERROR = "NETWORK_ERROR"
    CONNECTION_FAILED = "CONNECTION_FAILED"

    # Internal errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Error suggestions by code
ERROR_SUGGESTIONS: Dict[ErrorCode, str] = {
    ErrorCode.TOOL_NOT_FOUND: "Check the tool name spelling or list available tools.",
    ErrorCode.TOOL_DISABLED: "Enable the tool in settings or use an alternative tool.",
    ErrorCode.PERMISSION_DENIED: "Request permission or check access rules in settings.",
    ErrorCode.PERMISSION_PENDING: "Wait for user approval or modify permission rules.",
    ErrorCode.VALIDATION_ERROR: "Check the parameter values and types.",
    ErrorCode.INVALID_ARGUMENT: "Verify the argument format and allowed values.",
    ErrorCode.MISSING_ARGUMENT: "Provide all required arguments for the tool.",
    ErrorCode.EXECUTION_ERROR: "Check the operation and try again.",
    ErrorCode.COMMAND_FAILED: "Check the command syntax and ensure required programs are installed.",
    ErrorCode.TIMEOUT: "Increase timeout or break the operation into smaller parts.",
    ErrorCode.FILE_NOT_FOUND: "Verify the file path exists or create the file first.",
    ErrorCode.FILE_ACCESS_ERROR: "Check file permissions and ensure the file is not locked.",
    ErrorCode.FILE_EXISTS: "Use a different filename or delete the existing file first.",
    ErrorCode.DIRECTORY_NOT_FOUND: "Create the directory first or check the path.",
    ErrorCode.NETWORK_ERROR: "Check network connectivity and try again.",
    ErrorCode.CONNECTION_FAILED: "Verify the server address and network settings.",
    ErrorCode.INTERNAL_ERROR: "This is an internal error. Please report it.",
    ErrorCode.UNKNOWN_ERROR: "An unexpected error occurred. Check the details.",
}


@dataclass
class ToolError(Exception):
    """
    Unified error class for all tool errors.

    Provides:
    - Error code for categorization
    - Human-readable message
    - Tool name for context
    - Additional details
    - Recovery suggestion
    - Recoverable flag
    """

    code: ErrorCode
    message: str
    tool_name: str = ""
    details: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None
    recoverable: bool = True

    def __post_init__(self):
        """Initialize exception with message."""
        super().__init__(self.message)
        # Auto-fill suggestion if not provided
        if self.suggestion is None:
            self.suggestion = ERROR_SUGGESTIONS.get(self.code)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary.

        Returns:
            Dictionary representation of error
        """
        result = {
            "code": self.code.value,
            "message": self.message,
            "tool_name": self.tool_name,
            "recoverable": self.recoverable,
        }
        if self.details:
            result["details"] = self.details
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result

    def __str__(self) -> str:
        """String representation."""
        parts = [f"[{self.code.value}]"]
        if self.tool_name:
            parts.append(f"({self.tool_name})")
        parts.append(self.message)
        return " ".join(parts)


def get_error_suggestion(
    code: ErrorCode,
    tool_name: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Get a recovery suggestion for an error.

    Args:
        code: Error code
        tool_name: Tool name for context
        context: Additional context

    Returns:
        Suggestion string
    """
    base_suggestion = ERROR_SUGGESTIONS.get(code, "Check the error details.")

    # Add context-specific suggestions
    if context:
        if code == ErrorCode.FILE_NOT_FOUND and "file_path" in context:
            path = context["file_path"]
            return f"{base_suggestion} Path: {path}"

        if code == ErrorCode.COMMAND_FAILED and "command" in context:
            cmd = context["command"]
            if cmd.startswith("git "):
                return f"{base_suggestion} Ensure you're in a git repository."
            if cmd.startswith("npm ") or cmd.startswith("yarn "):
                return f"{base_suggestion} Ensure Node.js is installed and package.json exists."

        if code == ErrorCode.TIMEOUT and "command" in context:
            return f"{base_suggestion} Consider using a shorter timeout or running in background."

    return base_suggestion


def format_error(error: ToolError, verbose: bool = False) -> str:
    """
    Format error for logging/display.

    Args:
        error: ToolError to format
        verbose: Include details if True

    Returns:
        Formatted error string
    """
    lines = [f"Error [{error.code.value}]: {error.message}"]

    if error.tool_name:
        lines.append(f"  Tool: {error.tool_name}")

    if verbose and error.details:
        lines.append("  Details:")
        for key, value in error.details.items():
            lines.append(f"    {key}: {value}")

    if error.suggestion:
        lines.append(f"  Suggestion: {error.suggestion}")

    return "\n".join(lines)


def format_error_for_user(error: ToolError) -> str:
    """
    Format error for user-friendly display.

    Args:
        error: ToolError to format

    Returns:
        User-friendly error string
    """
    # Start with the main message
    result = error.message

    # Add suggestion if available
    if error.suggestion:
        result += f"\n\nSuggestion: {error.suggestion}"

    return result


# Factory functions for common errors


def create_file_not_found_error(tool_name: str, file_path: str) -> ToolError:
    """Create a file not found error."""
    return ToolError(
        code=ErrorCode.FILE_NOT_FOUND,
        message=f"File not found: {file_path}",
        tool_name=tool_name,
        details={"file_path": file_path},
        suggestion=get_error_suggestion(
            ErrorCode.FILE_NOT_FOUND,
            tool_name,
            {"file_path": file_path},
        ),
    )


def create_permission_denied_error(tool_name: str, target: str) -> ToolError:
    """Create a permission denied error."""
    return ToolError(
        code=ErrorCode.PERMISSION_DENIED,
        message=f"Permission denied: {target}",
        tool_name=tool_name,
        details={"target": target},
        recoverable=False,
    )


def create_validation_error(
    tool_name: str,
    parameter: str,
    reason: str,
) -> ToolError:
    """Create a validation error."""
    return ToolError(
        code=ErrorCode.VALIDATION_ERROR,
        message=f"Invalid parameter '{parameter}': {reason}",
        tool_name=tool_name,
        details={"parameter": parameter, "reason": reason},
    )


def create_timeout_error(
    tool_name: str,
    operation: str,
    timeout_ms: int,
) -> ToolError:
    """Create a timeout error."""
    return ToolError(
        code=ErrorCode.TIMEOUT,
        message=f"Operation timed out after {timeout_ms}ms: {operation}",
        tool_name=tool_name,
        details={"operation": operation, "timeout_ms": timeout_ms},
        suggestion=get_error_suggestion(
            ErrorCode.TIMEOUT,
            tool_name,
            {"command": operation},
        ),
    )


def create_command_failed_error(
    tool_name: str,
    command: str,
    exit_code: int,
    stderr: str = "",
) -> ToolError:
    """Create a command failed error."""
    message = f"Command failed with exit code {exit_code}: {command}"
    if stderr:
        message += f"\nStderr: {stderr[:500]}"  # Truncate long stderr

    return ToolError(
        code=ErrorCode.COMMAND_FAILED,
        message=message,
        tool_name=tool_name,
        details={
            "command": command,
            "exit_code": exit_code,
            "stderr": stderr[:1000] if stderr else "",
        },
        suggestion=get_error_suggestion(
            ErrorCode.COMMAND_FAILED,
            tool_name,
            {"command": command},
        ),
    )


def error_to_result(error: ToolError) -> ToolResult:
    """
    Convert a ToolError to a ToolResult.

    Args:
        error: ToolError to convert

    Returns:
        ToolResult with error information
    """
    output = error.message
    if error.suggestion:
        output += f"\n\nSuggestion: {error.suggestion}"

    metadata = {
        "error_code": error.code.value,
        "recoverable": error.recoverable,
    }
    if error.details:
        metadata["details"] = error.details
    if error.suggestion:
        metadata["suggestion"] = error.suggestion

    return ToolResult.error_result(
        tool_name=error.tool_name,
        error=error.message,
        output=output,
        metadata=metadata,
    )


def wrap_exception(
    exc: Exception,
    tool_name: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> ToolError:
    """
    Wrap a standard exception into a ToolError.

    Args:
        exc: Exception to wrap
        tool_name: Tool name for context
        context: Additional context

    Returns:
        ToolError wrapping the exception
    """
    # Map exception types to error codes
    if isinstance(exc, FileNotFoundError):
        return ToolError(
            code=ErrorCode.FILE_NOT_FOUND,
            message=str(exc),
            tool_name=tool_name,
            details=context,
        )

    if isinstance(exc, PermissionError):
        return ToolError(
            code=ErrorCode.PERMISSION_DENIED,
            message=str(exc),
            tool_name=tool_name,
            details=context,
            recoverable=False,
        )

    if isinstance(exc, subprocess.TimeoutExpired):
        return ToolError(
            code=ErrorCode.TIMEOUT,
            message=f"Command timed out: {exc.cmd}",
            tool_name=tool_name,
            details={"command": str(exc.cmd), "timeout": exc.timeout},
        )

    if isinstance(exc, subprocess.CalledProcessError):
        return ToolError(
            code=ErrorCode.COMMAND_FAILED,
            message=f"Command failed with exit code {exc.returncode}",
            tool_name=tool_name,
            details={
                "command": str(exc.cmd),
                "exit_code": exc.returncode,
                "stderr": exc.stderr[:1000] if exc.stderr else "",
            },
        )

    if isinstance(exc, IsADirectoryError):
        return ToolError(
            code=ErrorCode.FILE_ACCESS_ERROR,
            message=f"Expected file but got directory: {exc}",
            tool_name=tool_name,
            details=context,
        )

    if isinstance(exc, NotADirectoryError):
        return ToolError(
            code=ErrorCode.DIRECTORY_NOT_FOUND,
            message=f"Expected directory but got file: {exc}",
            tool_name=tool_name,
            details=context,
        )

    if isinstance(exc, OSError):
        return ToolError(
            code=ErrorCode.FILE_ACCESS_ERROR,
            message=str(exc),
            tool_name=tool_name,
            details=context,
        )

    if isinstance(exc, ValueError):
        return ToolError(
            code=ErrorCode.VALIDATION_ERROR,
            message=str(exc),
            tool_name=tool_name,
            details=context,
        )

    if isinstance(exc, TypeError):
        return ToolError(
            code=ErrorCode.INVALID_ARGUMENT,
            message=str(exc),
            tool_name=tool_name,
            details=context,
        )

    # Generic fallback
    return ToolError(
        code=ErrorCode.EXECUTION_ERROR,
        message=str(exc),
        tool_name=tool_name,
        details={"exception_type": type(exc).__name__, **(context or {})},
    )
