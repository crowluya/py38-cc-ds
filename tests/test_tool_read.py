"""
Tests for Read tool (T004)

Python 3.8.10 compatible
"""

import base64
import os
import tempfile
import pytest
from pathlib import Path

from claude_code.core.tools.read import ReadTool


class TestReadTool:
    """Tests for ReadTool."""

    def test_properties(self):
        """Test tool properties."""
        tool = ReadTool()
        assert tool.name == "Read"
        assert "file" in tool.description.lower()
        assert len(tool.parameters) == 3
        assert tool.requires_permission is True
        assert tool.is_dangerous is False

    def test_json_schema(self):
        """Test JSON schema generation."""
        tool = ReadTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "Read"
        assert "file_path" in schema["function"]["parameters"]["properties"]
        assert "offset" in schema["function"]["parameters"]["properties"]
        assert "limit" in schema["function"]["parameters"]["properties"]
        assert "file_path" in schema["function"]["parameters"]["required"]

    def test_read_text_file(self):
        """Test reading a text file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path})

            assert result.success is True
            assert "Line 1" in result.output
            assert "Line 2" in result.output
            assert "Line 3" in result.output
            # Check line numbers
            assert "1\t" in result.output
            assert "2\t" in result.output
            assert "3\t" in result.output
        finally:
            os.unlink(temp_path)

    def test_read_with_offset(self):
        """Test reading with offset."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path, "offset": 3})

            assert result.success is True
            assert "Line 1" not in result.output
            assert "Line 2" not in result.output
            assert "Line 3" in result.output
            assert "Line 4" in result.output
            assert "Line 5" in result.output
        finally:
            os.unlink(temp_path)

    def test_read_with_limit(self):
        """Test reading with limit."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path, "limit": 2})

            assert result.success is True
            assert "Line 1" in result.output
            assert "Line 2" in result.output
            assert "Line 3" not in result.output
            assert "more lines" in result.output
        finally:
            os.unlink(temp_path)

    def test_read_with_offset_and_limit(self):
        """Test reading with both offset and limit."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path, "offset": 2, "limit": 2})

            assert result.success is True
            assert "Line 1" not in result.output
            assert "Line 2" in result.output
            assert "Line 3" in result.output
            assert "Line 4" not in result.output
        finally:
            os.unlink(temp_path)

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        tool = ReadTool()
        result = tool.execute({"file_path": "/nonexistent/path/file.txt"})

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_read_directory(self):
        """Test reading a directory (should fail)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_dir})

            assert result.success is False
            assert "not a file" in result.error.lower()

    def test_read_binary_file(self):
        """Test reading a binary file."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"\x00\x01\x02\x03\x04\x05")
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path})

            assert result.success is True
            assert "binary" in result.output.lower() or "base64" in result.output.lower()
            assert result.metadata is not None
            assert "base64" in result.metadata
        finally:
            os.unlink(temp_path)

    def test_read_image_file(self):
        """Test reading an image file."""
        # Create a minimal PNG file
        png_header = b'\x89PNG\r\n\x1a\n'
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".png", delete=False) as f:
            f.write(png_header + b'\x00' * 100)
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path})

            assert result.success is True
            assert result.metadata is not None
            assert "base64" in result.metadata
        finally:
            os.unlink(temp_path)

    def test_read_empty_file(self):
        """Test reading an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path})

            assert result.success is True
            assert result.metadata["total_lines"] == 0
        finally:
            os.unlink(temp_path)

    def test_read_unicode_file(self):
        """Test reading a file with unicode content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello 世界\nПривет мир\n日本語\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path})

            assert result.success is True
            assert "世界" in result.output
            assert "Привет" in result.output
            assert "日本語" in result.output
        finally:
            os.unlink(temp_path)

    def test_read_long_lines_truncated(self):
        """Test that long lines are truncated."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("x" * 3000 + "\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path})

            assert result.success is True
            assert "truncated" in result.output.lower()
            # Line should be truncated to ~2000 chars
            assert len(result.output.split("\n")[0]) < 2500
        finally:
            os.unlink(temp_path)

    def test_offset_beyond_file(self):
        """Test offset beyond file length."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1\nLine 2\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path, "offset": 100})

            assert result.success is True
            assert "beyond" in result.output.lower()
        finally:
            os.unlink(temp_path)

    def test_metadata_included(self):
        """Test that metadata is included in result."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            result = tool.execute({"file_path": temp_path})

            assert result.success is True
            assert result.metadata is not None
            assert "total_lines" in result.metadata
            assert result.metadata["total_lines"] == 3
            assert "file_path" in result.metadata
        finally:
            os.unlink(temp_path)


class TestReadToolSecurity:
    """Security tests for ReadTool."""

    def test_path_traversal_blocked(self):
        """Test that path traversal is blocked when project_root is set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file outside project root
            outside_file = Path(temp_dir) / "outside.txt"
            outside_file.write_text("secret")

            # Create project root inside temp_dir
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            tool = ReadTool(project_root=str(project_root))

            # Try to read file outside project root
            result = tool.execute({"file_path": str(outside_file)})

            assert result.success is False
            assert "escapes" in result.error.lower()

    def test_path_traversal_with_dotdot(self):
        """Test that .. path traversal is blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            # Create a file in project
            (project_root / "test.txt").write_text("ok")

            tool = ReadTool(project_root=str(project_root))

            # Try to escape with ..
            result = tool.execute({"file_path": str(project_root / ".." / "escape.txt")})

            assert result.success is False

    def test_read_within_project_root(self):
        """Test that reading within project root works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            test_file = project_root / "test.txt"
            test_file.write_text("Hello")

            tool = ReadTool(project_root=str(project_root))
            result = tool.execute({"file_path": str(test_file)})

            assert result.success is True
            assert "Hello" in result.output

    def test_no_project_root_allows_all(self):
        """Test that without project_root, all paths are allowed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("content")
            temp_path = f.name

        try:
            tool = ReadTool()  # No project_root
            result = tool.execute({"file_path": temp_path})

            assert result.success is True
        finally:
            os.unlink(temp_path)


class TestReadToolValidation:
    """Validation tests for ReadTool."""

    def test_missing_file_path(self):
        """Test that missing file_path raises error."""
        tool = ReadTool()
        from claude_code.core.tools.base import ToolValidationError

        with pytest.raises(ToolValidationError):
            tool.execute({})

    def test_invalid_offset_corrected(self):
        """Test that invalid offset is corrected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            # Negative offset should be corrected to 1
            result = tool.execute({"file_path": temp_path, "offset": -5})

            assert result.success is True
            assert "Line 1" in result.output
        finally:
            os.unlink(temp_path)

    def test_limit_capped(self):
        """Test that limit is capped at maximum."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1\n")
            temp_path = f.name

        try:
            tool = ReadTool()
            # Very large limit should be capped
            result = tool.execute({"file_path": temp_path, "limit": 999999})

            assert result.success is True
            # Should still work, just capped
        finally:
            os.unlink(temp_path)
