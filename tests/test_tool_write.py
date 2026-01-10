"""
Tests for Write tool (T005)

Python 3.8.10 compatible
"""

import os
import tempfile
import pytest
from pathlib import Path

from claude_code.core.tools.write import WriteTool


class TestWriteTool:
    """Tests for WriteTool."""

    def test_properties(self):
        """Test tool properties."""
        tool = WriteTool()
        assert tool.name == "Write"
        assert "file" in tool.description.lower()
        assert len(tool.parameters) == 2
        assert tool.requires_permission is True
        assert tool.is_dangerous is True

    def test_json_schema(self):
        """Test JSON schema generation."""
        tool = WriteTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "Write"
        assert "file_path" in schema["function"]["parameters"]["properties"]
        assert "content" in schema["function"]["parameters"]["properties"]
        assert "file_path" in schema["function"]["parameters"]["required"]
        assert "content" in schema["function"]["parameters"]["required"]

    def test_write_new_file(self):
        """Test writing a new file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")

            tool = WriteTool()
            result = tool.execute({
                "file_path": file_path,
                "content": "Hello, World!",
            })

            assert result.success is True
            assert "Created" in result.output
            assert Path(file_path).exists()
            assert Path(file_path).read_text() == "Hello, World!"

    def test_overwrite_existing_file(self):
        """Test overwriting an existing file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Old content")
            temp_path = f.name

        try:
            tool = WriteTool()
            result = tool.execute({
                "file_path": temp_path,
                "content": "New content",
            })

            assert result.success is True
            assert "Overwrote" in result.output
            assert Path(temp_path).read_text() == "New content"
        finally:
            os.unlink(temp_path)

    def test_create_parent_directories(self):
        """Test that parent directories are created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "a", "b", "c", "test.txt")

            tool = WriteTool()
            result = tool.execute({
                "file_path": file_path,
                "content": "Deep file",
            })

            assert result.success is True
            assert Path(file_path).exists()
            assert Path(file_path).read_text() == "Deep file"

    def test_write_unicode_content(self):
        """Test writing unicode content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "unicode.txt")

            tool = WriteTool()
            result = tool.execute({
                "file_path": file_path,
                "content": "Hello 世界\nПривет мир\n日本語",
            })

            assert result.success is True
            content = Path(file_path).read_text(encoding="utf-8")
            assert "世界" in content
            assert "Привет" in content
            assert "日本語" in content

    def test_write_empty_content(self):
        """Test writing empty content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "empty.txt")

            tool = WriteTool()
            result = tool.execute({
                "file_path": file_path,
                "content": "",
            })

            assert result.success is True
            assert Path(file_path).exists()
            assert Path(file_path).read_text() == ""

    def test_write_multiline_content(self):
        """Test writing multiline content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "multiline.txt")

            content = "Line 1\nLine 2\nLine 3\n"
            tool = WriteTool()
            result = tool.execute({
                "file_path": file_path,
                "content": content,
            })

            assert result.success is True
            assert Path(file_path).read_text() == content
            # splitlines() returns 3 lines (trailing \n doesn't create empty line)
            assert result.metadata["lines"] == 3

    def test_write_to_directory_fails(self):
        """Test that writing to a directory fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = WriteTool()
            result = tool.execute({
                "file_path": temp_dir,
                "content": "content",
            })

            assert result.success is False
            assert "directory" in result.error.lower()

    def test_metadata_included(self):
        """Test that metadata is included in result."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")

            tool = WriteTool()
            result = tool.execute({
                "file_path": file_path,
                "content": "Hello",
            })

            assert result.success is True
            assert result.metadata is not None
            assert "file_path" in result.metadata
            assert "bytes_written" in result.metadata
            assert "lines" in result.metadata
            assert result.metadata["created"] is True
            assert result.metadata["overwritten"] is False


class TestWriteToolSecurity:
    """Security tests for WriteTool."""

    def test_path_traversal_blocked(self):
        """Test that path traversal is blocked when project_root is set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            # Try to write outside project root
            outside_path = Path(temp_dir) / "outside.txt"

            tool = WriteTool(project_root=str(project_root))
            result = tool.execute({
                "file_path": str(outside_path),
                "content": "malicious",
            })

            assert result.success is False
            assert "escapes" in result.error.lower()
            assert not outside_path.exists()

    def test_path_traversal_with_dotdot(self):
        """Test that .. path traversal is blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            tool = WriteTool(project_root=str(project_root))
            result = tool.execute({
                "file_path": str(project_root / ".." / "escape.txt"),
                "content": "malicious",
            })

            assert result.success is False

    def test_write_within_project_root(self):
        """Test that writing within project root works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            test_file = project_root / "test.txt"

            tool = WriteTool(project_root=str(project_root))
            result = tool.execute({
                "file_path": str(test_file),
                "content": "Hello",
            })

            assert result.success is True
            assert test_file.exists()

    def test_no_project_root_allows_all(self):
        """Test that without project_root, all paths are allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")

            tool = WriteTool()  # No project_root
            result = tool.execute({
                "file_path": file_path,
                "content": "content",
            })

            assert result.success is True


class TestWriteToolValidation:
    """Validation tests for WriteTool."""

    def test_missing_file_path(self):
        """Test that missing file_path raises error."""
        tool = WriteTool()
        from claude_code.core.tools.base import ToolValidationError

        with pytest.raises(ToolValidationError):
            tool.execute({"content": "hello"})

    def test_missing_content(self):
        """Test that missing content raises error."""
        tool = WriteTool()
        from claude_code.core.tools.base import ToolValidationError

        with pytest.raises(ToolValidationError):
            tool.execute({"file_path": "/tmp/test.txt"})
