"""
Tests for error handling optimization (T017)

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict, List, Optional


class TestErrorCode:
    """Tests for error codes."""

    def test_error_codes_defined(self):
        """Test that error codes are defined."""
        from claude_code.core.errors import ErrorCode

        assert hasattr(ErrorCode, "TOOL_NOT_FOUND")
        assert hasattr(ErrorCode, "PERMISSION_DENIED")
        assert hasattr(ErrorCode, "VALIDATION_ERROR")
        assert hasattr(ErrorCode, "EXECUTION_ERROR")
        assert hasattr(ErrorCode, "FILE_NOT_FOUND")
        assert hasattr(ErrorCode, "FILE_ACCESS_ERROR")
        assert hasattr(ErrorCode, "COMMAND_FAILED")
        assert hasattr(ErrorCode, "TIMEOUT")
        assert hasattr(ErrorCode, "NETWORK_ERROR")

    def test_error_code_values_unique(self):
        """Test that error code values are unique."""
        from claude_code.core.errors import ErrorCode

        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))


class TestToolError:
    """Tests for unified ToolError class."""

    def test_create_tool_error(self):
        """Test creating a tool error."""
        from claude_code.core.errors import ToolError, ErrorCode

        error = ToolError(
            code=ErrorCode.FILE_NOT_FOUND,
            message="File not found: /tmp/test.txt",
            tool_name="Read",
        )

        assert error.code == ErrorCode.FILE_NOT_FOUND
        assert "File not found" in error.message
        assert error.tool_name == "Read"

    def test_tool_error_with_details(self):
        """Test tool error with additional details."""
        from claude_code.core.errors import ToolError, ErrorCode

        error = ToolError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid parameter",
            tool_name="Write",
            details={"parameter": "file_path", "reason": "Path is empty"},
        )

        assert error.details is not None
        assert error.details["parameter"] == "file_path"

    def test_tool_error_with_suggestion(self):
        """Test tool error with recovery suggestion."""
        from claude_code.core.errors import ToolError, ErrorCode

        error = ToolError(
            code=ErrorCode.FILE_NOT_FOUND,
            message="File not found",
            tool_name="Read",
            suggestion="Check if the file path is correct or create the file first.",
        )

        assert error.suggestion is not None
        assert "Check" in error.suggestion

    def test_tool_error_to_dict(self):
        """Test converting tool error to dictionary."""
        from claude_code.core.errors import ToolError, ErrorCode

        error = ToolError(
            code=ErrorCode.PERMISSION_DENIED,
            message="Access denied",
            tool_name="Write",
            suggestion="Request permission first.",
        )

        error_dict = error.to_dict()

        assert error_dict["code"] == ErrorCode.PERMISSION_DENIED.value
        assert error_dict["message"] == "Access denied"
        assert error_dict["tool_name"] == "Write"
        assert error_dict["suggestion"] == "Request permission first."

    def test_tool_error_str(self):
        """Test string representation of tool error."""
        from claude_code.core.errors import ToolError, ErrorCode

        error = ToolError(
            code=ErrorCode.TIMEOUT,
            message="Operation timed out",
            tool_name="Bash",
        )

        error_str = str(error)
        assert "TIMEOUT" in error_str or "timed out" in error_str.lower()

    def test_tool_error_is_recoverable(self):
        """Test checking if error is recoverable."""
        from claude_code.core.errors import ToolError, ErrorCode

        # Recoverable error
        error1 = ToolError(
            code=ErrorCode.TIMEOUT,
            message="Timed out",
            tool_name="Bash",
            recoverable=True,
        )
        assert error1.recoverable is True

        # Non-recoverable error
        error2 = ToolError(
            code=ErrorCode.PERMISSION_DENIED,
            message="Denied",
            tool_name="Write",
            recoverable=False,
        )
        assert error2.recoverable is False


class TestErrorFormatter:
    """Tests for error formatting."""

    def test_format_error_simple(self):
        """Test formatting a simple error."""
        from claude_code.core.errors import ToolError, ErrorCode, format_error

        error = ToolError(
            code=ErrorCode.FILE_NOT_FOUND,
            message="File not found: /tmp/test.txt",
            tool_name="Read",
        )

        formatted = format_error(error)

        assert "Read" in formatted
        assert "File not found" in formatted

    def test_format_error_with_suggestion(self):
        """Test formatting error with suggestion."""
        from claude_code.core.errors import ToolError, ErrorCode, format_error

        error = ToolError(
            code=ErrorCode.FILE_NOT_FOUND,
            message="File not found",
            tool_name="Read",
            suggestion="Create the file first using Write tool.",
        )

        formatted = format_error(error)

        assert "suggestion" in formatted.lower() or "Create" in formatted

    def test_format_error_verbose(self):
        """Test verbose error formatting."""
        from claude_code.core.errors import ToolError, ErrorCode, format_error

        error = ToolError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid parameter",
            tool_name="Write",
            details={"parameter": "content", "max_size": 1000000},
        )

        formatted = format_error(error, verbose=True)

        assert "parameter" in formatted.lower()

    def test_format_error_for_user(self):
        """Test user-friendly error formatting."""
        from claude_code.core.errors import ToolError, ErrorCode, format_error_for_user

        error = ToolError(
            code=ErrorCode.PERMISSION_DENIED,
            message="Permission denied for /etc/passwd",
            tool_name="Read",
            suggestion="This file requires elevated permissions.",
        )

        formatted = format_error_for_user(error)

        # Should be user-friendly, not technical
        assert "Permission" in formatted or "denied" in formatted.lower()


class TestErrorSuggestions:
    """Tests for error recovery suggestions."""

    def test_get_suggestion_file_not_found(self):
        """Test suggestion for file not found error."""
        from claude_code.core.errors import ErrorCode, get_error_suggestion

        suggestion = get_error_suggestion(
            ErrorCode.FILE_NOT_FOUND,
            tool_name="Read",
            context={"file_path": "/tmp/missing.txt"},
        )

        assert suggestion is not None
        assert len(suggestion) > 0

    def test_get_suggestion_permission_denied(self):
        """Test suggestion for permission denied error."""
        from claude_code.core.errors import ErrorCode, get_error_suggestion

        suggestion = get_error_suggestion(
            ErrorCode.PERMISSION_DENIED,
            tool_name="Write",
            context={"file_path": "/etc/passwd"},
        )

        assert suggestion is not None

    def test_get_suggestion_timeout(self):
        """Test suggestion for timeout error."""
        from claude_code.core.errors import ErrorCode, get_error_suggestion

        suggestion = get_error_suggestion(
            ErrorCode.TIMEOUT,
            tool_name="Bash",
            context={"command": "sleep 1000"},
        )

        assert suggestion is not None

    def test_get_suggestion_validation_error(self):
        """Test suggestion for validation error."""
        from claude_code.core.errors import ErrorCode, get_error_suggestion

        suggestion = get_error_suggestion(
            ErrorCode.VALIDATION_ERROR,
            tool_name="Write",
            context={"parameter": "file_path", "value": ""},
        )

        assert suggestion is not None

    def test_get_suggestion_command_failed(self):
        """Test suggestion for command failed error."""
        from claude_code.core.errors import ErrorCode, get_error_suggestion

        suggestion = get_error_suggestion(
            ErrorCode.COMMAND_FAILED,
            tool_name="Bash",
            context={"command": "git push", "exit_code": 1},
        )

        assert suggestion is not None


class TestErrorFactory:
    """Tests for error factory functions."""

    def test_create_file_not_found_error(self):
        """Test creating file not found error."""
        from claude_code.core.errors import create_file_not_found_error

        error = create_file_not_found_error("Read", "/tmp/missing.txt")

        assert error.code.value == "FILE_NOT_FOUND" or "FILE_NOT_FOUND" in str(error.code)
        assert "/tmp/missing.txt" in error.message
        assert error.suggestion is not None

    def test_create_permission_denied_error(self):
        """Test creating permission denied error."""
        from claude_code.core.errors import create_permission_denied_error

        error = create_permission_denied_error("Write", "/etc/passwd")

        assert "PERMISSION" in str(error.code)
        assert error.suggestion is not None

    def test_create_validation_error(self):
        """Test creating validation error."""
        from claude_code.core.errors import create_validation_error

        error = create_validation_error(
            "Write",
            parameter="file_path",
            reason="Path cannot be empty",
        )

        assert "VALIDATION" in str(error.code)
        assert "file_path" in error.message or error.details.get("parameter") == "file_path"

    def test_create_timeout_error(self):
        """Test creating timeout error."""
        from claude_code.core.errors import create_timeout_error

        error = create_timeout_error("Bash", "long_running_command", timeout_ms=30000)

        assert "TIMEOUT" in str(error.code)
        assert error.suggestion is not None

    def test_create_command_failed_error(self):
        """Test creating command failed error."""
        from claude_code.core.errors import create_command_failed_error

        error = create_command_failed_error(
            "Bash",
            command="git push",
            exit_code=1,
            stderr="Permission denied",
        )

        assert "COMMAND" in str(error.code)
        assert error.details is not None


class TestErrorResult:
    """Tests for converting errors to ToolResult."""

    def test_error_to_tool_result(self):
        """Test converting error to ToolResult."""
        from claude_code.core.errors import ToolError, ErrorCode, error_to_result

        error = ToolError(
            code=ErrorCode.FILE_NOT_FOUND,
            message="File not found",
            tool_name="Read",
            suggestion="Check the path",
        )

        result = error_to_result(error)

        assert result.success is False
        assert result.tool_name == "Read"
        assert "File not found" in result.error
        assert result.metadata is not None
        assert result.metadata.get("error_code") == ErrorCode.FILE_NOT_FOUND.value

    def test_error_result_includes_suggestion(self):
        """Test that error result includes suggestion in output."""
        from claude_code.core.errors import ToolError, ErrorCode, error_to_result

        error = ToolError(
            code=ErrorCode.PERMISSION_DENIED,
            message="Access denied",
            tool_name="Write",
            suggestion="Request write permission first.",
        )

        result = error_to_result(error)

        # Suggestion should be in output or metadata
        assert "suggestion" in result.metadata or "Request" in result.output


class TestErrorChaining:
    """Tests for error chaining and wrapping."""

    def test_wrap_exception(self):
        """Test wrapping a standard exception."""
        from claude_code.core.errors import wrap_exception

        try:
            raise FileNotFoundError("No such file: /tmp/test.txt")
        except FileNotFoundError as e:
            error = wrap_exception(e, tool_name="Read")

        assert error is not None
        assert error.tool_name == "Read"
        assert "FILE_NOT_FOUND" in str(error.code)

    def test_wrap_permission_error(self):
        """Test wrapping a permission error."""
        from claude_code.core.errors import wrap_exception

        try:
            raise PermissionError("Access denied")
        except PermissionError as e:
            error = wrap_exception(e, tool_name="Write")

        assert "PERMISSION" in str(error.code)

    def test_wrap_timeout_error(self):
        """Test wrapping a timeout error."""
        from claude_code.core.errors import wrap_exception
        import subprocess

        try:
            raise subprocess.TimeoutExpired("cmd", 30)
        except subprocess.TimeoutExpired as e:
            error = wrap_exception(e, tool_name="Bash")

        assert "TIMEOUT" in str(error.code)

    def test_wrap_generic_exception(self):
        """Test wrapping a generic exception."""
        from claude_code.core.errors import wrap_exception

        try:
            raise ValueError("Something went wrong")
        except ValueError as e:
            error = wrap_exception(e, tool_name="Unknown")

        assert error is not None
        assert "EXECUTION" in str(error.code) or "ERROR" in str(error.code)


class TestErrorIntegration:
    """Integration tests for error handling."""

    def test_full_error_workflow(self):
        """Test full error handling workflow."""
        from claude_code.core.errors import (
            create_file_not_found_error,
            format_error,
            format_error_for_user,
            error_to_result,
        )

        # Create error
        error = create_file_not_found_error("Read", "/tmp/missing.txt")

        # Format for logging
        log_format = format_error(error, verbose=True)
        assert len(log_format) > 0

        # Format for user
        user_format = format_error_for_user(error)
        assert len(user_format) > 0

        # Convert to result
        result = error_to_result(error)
        assert result.success is False
        assert result.metadata is not None

    def test_error_handling_in_executor(self):
        """Test error handling integration with executor."""
        from claude_code.core.errors import ToolError, ErrorCode
        from claude_code.core.tools.base import Tool, ToolResult, ToolCategory
        from claude_code.core.tools.registry import ToolRegistry
        from claude_code.core.tools.executor import ToolExecutor
        from claude_code.security.permissions import (
            PermissionManager,
            PermissionRule,
            PermissionAction,
            PermissionDomain,
        )

        class FailingTool(Tool):
            @property
            def name(self):
                return "FailingTool"

            @property
            def description(self):
                return "A tool that fails"

            @property
            def category(self):
                return ToolCategory.UTILITY

            @property
            def requires_permission(self):
                return False

            def execute(self, arguments):
                raise FileNotFoundError("Test file not found")

        registry = ToolRegistry()
        registry.register(FailingTool())

        executor = ToolExecutor(registry)
        result = executor.execute("FailingTool", {})

        assert result.success is False
        assert "error" in result.error.lower() or "not found" in result.error.lower()
