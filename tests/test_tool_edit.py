"""
Tests for Edit tool (T006)

Python 3.8.10 compatible
"""

import os
import tempfile
import pytest
from pathlib import Path

from deep_code.core.tools.edit import EditTool


class TestEditTool:
    """Tests for EditTool."""

    def test_properties(self):
        """Test tool properties."""
        tool = EditTool()
        assert tool.name == "Edit"
        assert "replace" in tool.description.lower()
        assert len(tool.parameters) == 4
        assert tool.requires_permission is True
        assert tool.is_dangerous is True

    def test_json_schema(self):
        """Test JSON schema generation."""
        tool = EditTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "Edit"
        assert "file_path" in schema["function"]["parameters"]["properties"]
        assert "old_string" in schema["function"]["parameters"]["properties"]
        assert "new_string" in schema["function"]["parameters"]["properties"]
        assert "replace_all" in schema["function"]["parameters"]["properties"]
        assert "file_path" in schema["function"]["parameters"]["required"]
        assert "old_string" in schema["function"]["parameters"]["required"]
        assert "new_string" in schema["function"]["parameters"]["required"]

    def test_simple_replacement(self):
        """Test simple string replacement."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello World")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "World",
                "new_string": "Python",
            })

            assert result.success is True
            assert Path(temp_path).read_text(encoding="utf-8") == "Hello Python"
        finally:
            os.unlink(temp_path)

    def test_multiline_replacement(self):
        """Test multiline string replacement."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "Line 2\nLine 3",
                "new_string": "New Line 2\nNew Line 3\nNew Line 4",
            })

            assert result.success is True
            content = Path(temp_path).read_text(encoding="utf-8")
            assert "New Line 2" in content
            assert "New Line 3" in content
            assert "New Line 4" in content
        finally:
            os.unlink(temp_path)

    def test_old_string_not_found(self):
        """Test error when old_string is not found."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello World")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "NotFound",
                "new_string": "Replacement",
            })

            assert result.success is False
            assert "not found" in result.error.lower()
            # File should be unchanged
            assert Path(temp_path).read_text(encoding="utf-8") == "Hello World"
        finally:
            os.unlink(temp_path)

    def test_old_string_not_unique(self):
        """Test error when old_string appears multiple times."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello Hello Hello")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "Hello",
                "new_string": "Hi",
            })

            assert result.success is False
            assert "unique" in result.error.lower() or "multiple" in result.error.lower()
            # File should be unchanged
            assert Path(temp_path).read_text(encoding="utf-8") == "Hello Hello Hello"
        finally:
            os.unlink(temp_path)

    def test_replace_all(self):
        """Test replace_all parameter."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello Hello Hello")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "Hello",
                "new_string": "Hi",
                "replace_all": True,
            })

            assert result.success is True
            assert Path(temp_path).read_text(encoding="utf-8") == "Hi Hi Hi"
            assert result.metadata["replacements"] == 3
        finally:
            os.unlink(temp_path)

    def test_replace_all_count(self):
        """Test that replace_all reports correct count."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("a b a c a d a")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "a",
                "new_string": "X",
                "replace_all": True,
            })

            assert result.success is True
            assert Path(temp_path).read_text(encoding="utf-8") == "X b X c X d X"
            assert result.metadata["replacements"] == 4
        finally:
            os.unlink(temp_path)

    def test_file_not_found(self):
        """Test error when file doesn't exist."""
        tool = EditTool()
        result = tool.execute({
            "file_path": "/nonexistent/path/file.txt",
            "old_string": "old",
            "new_string": "new",
        })

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_edit_directory_fails(self):
        """Test that editing a directory fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_dir,
                "old_string": "old",
                "new_string": "new",
            })

            assert result.success is False
            assert "not a file" in result.error.lower()

    def test_unicode_replacement(self):
        """Test unicode string replacement."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello 世界")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "世界",
                "new_string": "Python",
            })

            assert result.success is True
            assert Path(temp_path).read_text(encoding="utf-8") == "Hello Python"
        finally:
            os.unlink(temp_path)

    def test_empty_old_string(self):
        """Test that empty old_string fails."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello World")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "",
                "new_string": "new",
            })

            assert result.success is False
            assert "empty" in result.error.lower()
        finally:
            os.unlink(temp_path)

    def test_same_old_new_string(self):
        """Test that same old and new string fails."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello World")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "Hello",
                "new_string": "Hello",
            })

            assert result.success is False
            assert "same" in result.error.lower() or "different" in result.error.lower()
        finally:
            os.unlink(temp_path)

    def test_metadata_included(self):
        """Test that metadata is included in result."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello World")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "World",
                "new_string": "Python",
            })

            assert result.success is True
            assert result.metadata is not None
            assert "file_path" in result.metadata
            assert "replacements" in result.metadata
            assert result.metadata["replacements"] == 1
        finally:
            os.unlink(temp_path)

    def test_preserve_file_encoding(self):
        """Test that file encoding is preserved."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("日本語テスト")
            temp_path = f.name

        try:
            tool = EditTool()
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "テスト",
                "new_string": "成功",
            })

            assert result.success is True
            content = Path(temp_path).read_text(encoding="utf-8")
            assert content == "日本語成功"
        finally:
            os.unlink(temp_path)


class TestEditToolSecurity:
    """Security tests for EditTool."""

    def test_path_traversal_blocked(self):
        """Test that path traversal is blocked when project_root is set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            # Create file outside project root
            outside_file = Path(temp_dir) / "outside.txt"
            outside_file.write_text("secret content")

            tool = EditTool(project_root=str(project_root))
            result = tool.execute({
                "file_path": str(outside_file),
                "old_string": "secret",
                "new_string": "modified",
            })

            assert result.success is False
            assert "escapes" in result.error.lower()
            # File should be unchanged
            assert outside_file.read_text() == "secret content"

    def test_path_traversal_with_dotdot(self):
        """Test that .. path traversal is blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            tool = EditTool(project_root=str(project_root))
            result = tool.execute({
                "file_path": str(project_root / ".." / "escape.txt"),
                "old_string": "old",
                "new_string": "new",
            })

            assert result.success is False

    def test_edit_within_project_root(self):
        """Test that editing within project root works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            test_file = project_root / "test.txt"
            test_file.write_text("Hello World")

            tool = EditTool(project_root=str(project_root))
            result = tool.execute({
                "file_path": str(test_file),
                "old_string": "World",
                "new_string": "Python",
            })

            assert result.success is True
            assert test_file.read_text() == "Hello Python"

    def test_no_project_root_allows_all(self):
        """Test that without project_root, all paths are allowed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello World")
            temp_path = f.name

        try:
            tool = EditTool()  # No project_root
            result = tool.execute({
                "file_path": temp_path,
                "old_string": "World",
                "new_string": "Python",
            })

            assert result.success is True
        finally:
            os.unlink(temp_path)


class TestEditToolValidation:
    """Validation tests for EditTool."""

    def test_missing_file_path(self):
        """Test that missing file_path raises error."""
        tool = EditTool()
        from deep_code.core.tools.base import ToolValidationError

        with pytest.raises(ToolValidationError):
            tool.execute({
                "old_string": "old",
                "new_string": "new",
            })

    def test_missing_old_string(self):
        """Test that missing old_string raises error."""
        tool = EditTool()
        from deep_code.core.tools.base import ToolValidationError

        with pytest.raises(ToolValidationError):
            tool.execute({
                "file_path": "/tmp/test.txt",
                "new_string": "new",
            })

    def test_missing_new_string(self):
        """Test that missing new_string raises error."""
        tool = EditTool()
        from deep_code.core.tools.base import ToolValidationError

        with pytest.raises(ToolValidationError):
            tool.execute({
                "file_path": "/tmp/test.txt",
                "old_string": "old",
            })
