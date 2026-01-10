"""
Tests for Bash tool (T007)

Python 3.8.10 compatible
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

from claude_code.core.tools.bash import BashTool


class TestBashTool:
    """Tests for BashTool."""

    def test_properties(self):
        """Test tool properties."""
        tool = BashTool()
        assert tool.name == "Bash"
        assert "command" in tool.description.lower()
        assert len(tool.parameters) == 3
        assert tool.requires_permission is True
        assert tool.is_dangerous is True

    def test_json_schema(self):
        """Test JSON schema generation."""
        tool = BashTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "Bash"
        assert "command" in schema["function"]["parameters"]["properties"]
        assert "timeout" in schema["function"]["parameters"]["properties"]
        assert "working_dir" in schema["function"]["parameters"]["properties"]
        assert "command" in schema["function"]["parameters"]["required"]

    def test_simple_command(self):
        """Test simple command execution."""
        tool = BashTool()
        result = tool.execute({"command": "echo hello"})

        assert result.success is True
        assert "hello" in result.output

    def test_command_with_arguments(self):
        """Test command with arguments."""
        tool = BashTool()
        result = tool.execute({"command": "echo hello world"})

        assert result.success is True
        assert "hello world" in result.output

    def test_command_return_code(self):
        """Test command return code in metadata."""
        tool = BashTool()
        result = tool.execute({"command": "echo test"})

        assert result.success is True
        assert result.metadata is not None
        assert result.metadata["return_code"] == 0

    def test_failed_command(self):
        """Test failed command."""
        tool = BashTool()
        # Use a command that will fail
        result = tool.execute({"command": "exit 1"})

        assert result.success is False
        assert result.metadata["return_code"] == 1

    def test_command_not_found(self):
        """Test command not found."""
        tool = BashTool()
        result = tool.execute({"command": "nonexistent_command_xyz123"})

        assert result.success is False

    def test_working_directory(self):
        """Test working directory parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = BashTool()
            # pwd on Unix, cd on Windows
            if sys.platform == "win32":
                result = tool.execute({
                    "command": "cd",
                    "working_dir": temp_dir,
                })
            else:
                result = tool.execute({
                    "command": "pwd",
                    "working_dir": temp_dir,
                })

            assert result.success is True
            # The output should contain the temp directory path
            assert temp_dir in result.output or Path(temp_dir).name in result.output

    def test_timeout(self):
        """Test timeout parameter."""
        tool = BashTool()
        # Use a command that takes longer than timeout
        if sys.platform == "win32":
            result = tool.execute({
                "command": "ping -n 10 127.0.0.1",
                "timeout": 1,
            })
        else:
            result = tool.execute({
                "command": "sleep 10",
                "timeout": 1,
            })

        assert result.success is False
        assert result.metadata["timed_out"] is True

    def test_capture_stdout(self):
        """Test stdout capture."""
        tool = BashTool()
        result = tool.execute({"command": "echo stdout_test"})

        assert result.success is True
        assert "stdout_test" in result.output

    def test_capture_stderr(self):
        """Test stderr capture."""
        tool = BashTool()
        if sys.platform == "win32":
            result = tool.execute({"command": "echo stderr_test 1>&2"})
        else:
            result = tool.execute({"command": "echo stderr_test >&2"})

        assert result.success is True
        # stderr should be in output or metadata
        assert "stderr_test" in result.output or "stderr_test" in result.metadata.get("stderr", "")

    def test_multiline_output(self):
        """Test multiline output."""
        tool = BashTool()
        if sys.platform == "win32":
            result = tool.execute({"command": "echo line1 & echo line2 & echo line3"})
        else:
            result = tool.execute({"command": "echo line1; echo line2; echo line3"})

        assert result.success is True
        assert "line1" in result.output
        assert "line2" in result.output
        assert "line3" in result.output

    def test_unicode_output(self):
        """Test unicode output handling."""
        tool = BashTool()
        if sys.platform == "win32":
            # Windows echo doesn't handle unicode well, use python
            result = tool.execute({"command": 'python -c "print(\'Hello 世界\')"'})
        else:
            result = tool.execute({"command": "echo 'Hello 世界'"})

        assert result.success is True
        assert "Hello" in result.output

    def test_metadata_included(self):
        """Test that metadata is included in result."""
        tool = BashTool()
        result = tool.execute({"command": "echo test"})

        assert result.success is True
        assert result.metadata is not None
        assert "command" in result.metadata
        assert "return_code" in result.metadata
        assert "timed_out" in result.metadata


class TestBashToolDangerousCommands:
    """Tests for dangerous command detection."""

    def test_rm_rf_detected(self):
        """Test that rm -rf is detected as dangerous."""
        tool = BashTool()
        result = tool.execute({"command": "rm -rf /"})

        assert result.success is False
        assert "dangerous" in result.error.lower()

    def test_rm_rf_with_path_detected(self):
        """Test that rm -rf with path is detected."""
        tool = BashTool()
        result = tool.execute({"command": "rm -rf /home/user"})

        assert result.success is False
        assert "dangerous" in result.error.lower()

    def test_rm_rf_variations(self):
        """Test various rm -rf variations."""
        tool = BashTool()

        dangerous_commands = [
            "rm -rf /",
            "rm -rf /*",
            "rm -rf ~",
            "rm -rf ~/",
            "rm -fr /",
            "rm --recursive --force /",
        ]

        for cmd in dangerous_commands:
            result = tool.execute({"command": cmd})
            assert result.success is False, f"Command should be blocked: {cmd}"

    def test_safe_rm_allowed(self):
        """Test that safe rm commands are allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test")

            tool = BashTool()
            result = tool.execute({"command": f"rm {test_file}"})

            # Should succeed (file deleted)
            assert result.success is True
            assert not test_file.exists()

    def test_mkfs_detected(self):
        """Test that mkfs is detected as dangerous."""
        tool = BashTool()
        result = tool.execute({"command": "mkfs.ext4 /dev/sda"})

        assert result.success is False
        assert "dangerous" in result.error.lower()

    def test_dd_to_device_detected(self):
        """Test that dd to device is detected as dangerous."""
        tool = BashTool()
        result = tool.execute({"command": "dd if=/dev/zero of=/dev/sda"})

        assert result.success is False
        assert "dangerous" in result.error.lower()

    def test_chmod_777_root_detected(self):
        """Test that chmod 777 / is detected as dangerous."""
        tool = BashTool()
        result = tool.execute({"command": "chmod -R 777 /"})

        assert result.success is False
        assert "dangerous" in result.error.lower()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_format_detected_windows(self):
        """Test that format command is detected on Windows."""
        tool = BashTool()
        result = tool.execute({"command": "format C:"})

        assert result.success is False
        assert "dangerous" in result.error.lower()


class TestBashToolSecurity:
    """Security tests for BashTool."""

    def test_working_dir_must_exist(self):
        """Test that working_dir must exist."""
        tool = BashTool()
        result = tool.execute({
            "command": "echo test",
            "working_dir": "/nonexistent/path/xyz123",
        })

        assert result.success is False
        assert "not found" in result.error.lower() or "not exist" in result.error.lower()

    def test_working_dir_must_be_directory(self):
        """Test that working_dir must be a directory."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            tool = BashTool()
            result = tool.execute({
                "command": "echo test",
                "working_dir": temp_file,
            })

            assert result.success is False
            assert "not a directory" in result.error.lower()
        finally:
            os.unlink(temp_file)

    def test_project_root_restricts_working_dir(self):
        """Test that project_root restricts working_dir."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            outside_dir = Path(temp_dir) / "outside"
            outside_dir.mkdir()

            tool = BashTool(project_root=str(project_root))
            result = tool.execute({
                "command": "echo test",
                "working_dir": str(outside_dir),
            })

            assert result.success is False
            assert "escapes" in result.error.lower()

    def test_working_dir_within_project_root(self):
        """Test that working_dir within project_root works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            subdir = project_root / "subdir"
            subdir.mkdir()

            tool = BashTool(project_root=str(project_root))
            result = tool.execute({
                "command": "echo test",
                "working_dir": str(subdir),
            })

            assert result.success is True


class TestBashToolValidation:
    """Validation tests for BashTool."""

    def test_missing_command(self):
        """Test that missing command raises error."""
        tool = BashTool()
        from claude_code.core.tools.base import ToolValidationError

        with pytest.raises(ToolValidationError):
            tool.execute({})

    def test_empty_command(self):
        """Test that empty command fails."""
        tool = BashTool()
        result = tool.execute({"command": ""})

        assert result.success is False
        assert "empty" in result.error.lower()

    def test_whitespace_only_command(self):
        """Test that whitespace-only command fails."""
        tool = BashTool()
        result = tool.execute({"command": "   "})

        assert result.success is False
        assert "empty" in result.error.lower()

    def test_timeout_must_be_positive(self):
        """Test that timeout must be positive."""
        tool = BashTool()
        result = tool.execute({
            "command": "echo test",
            "timeout": -1,
        })

        # Should use default timeout instead of negative
        assert result.success is True

    def test_timeout_capped_at_maximum(self):
        """Test that timeout is capped at maximum."""
        tool = BashTool()
        # Very large timeout should be capped
        result = tool.execute({
            "command": "echo test",
            "timeout": 999999,
        })

        assert result.success is True
        # Timeout should be capped (check metadata if available)
