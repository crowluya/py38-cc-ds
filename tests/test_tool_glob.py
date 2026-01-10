"""
Tests for Glob tool (T008)

Python 3.8.10 compatible
"""

import os
import tempfile
import time
import pytest
from pathlib import Path

from claude_code.core.tools.glob import GlobTool


class TestGlobTool:
    """Tests for GlobTool."""

    def test_properties(self):
        """Test tool properties."""
        tool = GlobTool()
        assert tool.name == "Glob"
        assert "pattern" in tool.description.lower()
        assert len(tool.parameters) == 3
        assert tool.requires_permission is True
        assert tool.is_dangerous is False

    def test_json_schema(self):
        """Test JSON schema generation."""
        tool = GlobTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "Glob"
        assert "pattern" in schema["function"]["parameters"]["properties"]
        assert "path" in schema["function"]["parameters"]["properties"]
        assert "limit" in schema["function"]["parameters"]["properties"]
        assert "pattern" in schema["function"]["parameters"]["required"]

    def test_simple_pattern(self):
        """Test simple glob pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            (Path(temp_dir) / "test1.txt").write_text("content1")
            (Path(temp_dir) / "test2.txt").write_text("content2")
            (Path(temp_dir) / "test3.py").write_text("content3")

            tool = GlobTool()
            result = tool.execute({
                "pattern": "*.txt",
                "path": temp_dir,
            })

            assert result.success is True
            assert "test1.txt" in result.output
            assert "test2.txt" in result.output
            assert "test3.py" not in result.output

    def test_recursive_pattern(self):
        """Test recursive glob pattern (**)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            (Path(temp_dir) / "root.py").write_text("root")
            (subdir / "nested.py").write_text("nested")

            tool = GlobTool()
            result = tool.execute({
                "pattern": "**/*.py",
                "path": temp_dir,
            })

            assert result.success is True
            assert "root.py" in result.output
            assert "nested.py" in result.output

    def test_no_matches(self):
        """Test pattern with no matches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "test.txt").write_text("content")

            tool = GlobTool()
            result = tool.execute({
                "pattern": "*.xyz",
                "path": temp_dir,
            })

            assert result.success is True
            assert "no matches" in result.output.lower() or result.metadata["count"] == 0

    def test_limit_results(self):
        """Test limit parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many files
            for i in range(10):
                (Path(temp_dir) / f"file{i}.txt").write_text(f"content{i}")

            tool = GlobTool()
            result = tool.execute({
                "pattern": "*.txt",
                "path": temp_dir,
                "limit": 3,
            })

            assert result.success is True
            assert result.metadata["count"] == 3
            # Should indicate more files exist
            assert "more" in result.output.lower() or result.metadata.get("truncated", False)

    def test_default_path(self):
        """Test default path (current directory)."""
        tool = GlobTool()
        result = tool.execute({
            "pattern": "*.py",
        })

        # Should work without error
        assert result.success is True

    def test_sorted_by_mtime(self):
        """Test that results are sorted by modification time."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with different mtimes
            file1 = Path(temp_dir) / "old.txt"
            file2 = Path(temp_dir) / "new.txt"

            file1.write_text("old")
            time.sleep(0.1)  # Ensure different mtime
            file2.write_text("new")

            tool = GlobTool()
            result = tool.execute({
                "pattern": "*.txt",
                "path": temp_dir,
            })

            assert result.success is True
            # Newer file should come first (most recent first)
            output_lines = result.output.strip().split("\n")
            # Find lines containing filenames
            file_lines = [l for l in output_lines if ".txt" in l]
            if len(file_lines) >= 2:
                # new.txt should appear before old.txt
                new_idx = next((i for i, l in enumerate(file_lines) if "new.txt" in l), -1)
                old_idx = next((i for i, l in enumerate(file_lines) if "old.txt" in l), -1)
                assert new_idx < old_idx, "Files should be sorted by mtime (newest first)"

    def test_metadata_included(self):
        """Test that metadata is included in result."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "test.txt").write_text("content")

            tool = GlobTool()
            result = tool.execute({
                "pattern": "*.txt",
                "path": temp_dir,
            })

            assert result.success is True
            assert result.metadata is not None
            assert "count" in result.metadata
            assert "pattern" in result.metadata

    def test_complex_pattern(self):
        """Test complex glob patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create various files
            (Path(temp_dir) / "test.py").write_text("py")
            (Path(temp_dir) / "test.txt").write_text("txt")
            (Path(temp_dir) / "test.md").write_text("md")
            (Path(temp_dir) / "other.py").write_text("other")

            tool = GlobTool()
            result = tool.execute({
                "pattern": "test.*",
                "path": temp_dir,
            })

            assert result.success is True
            assert "test.py" in result.output
            assert "test.txt" in result.output
            assert "test.md" in result.output
            assert "other.py" not in result.output

    def test_hidden_files_excluded_by_default(self):
        """Test that hidden files are excluded by default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "visible.txt").write_text("visible")
            (Path(temp_dir) / ".hidden.txt").write_text("hidden")

            tool = GlobTool()
            result = tool.execute({
                "pattern": "*.txt",
                "path": temp_dir,
            })

            assert result.success is True
            assert "visible.txt" in result.output
            # Hidden files should be excluded by default
            assert ".hidden.txt" not in result.output


class TestGlobToolSecurity:
    """Security tests for GlobTool."""

    def test_path_traversal_blocked(self):
        """Test that path traversal is blocked when project_root is set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            outside_dir = Path(temp_dir) / "outside"
            outside_dir.mkdir()
            (outside_dir / "secret.txt").write_text("secret")

            tool = GlobTool(project_root=str(project_root))
            result = tool.execute({
                "pattern": "*.txt",
                "path": str(outside_dir),
            })

            assert result.success is False
            assert "escapes" in result.error.lower()

    def test_path_traversal_with_dotdot(self):
        """Test that .. path traversal is blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            tool = GlobTool(project_root=str(project_root))
            result = tool.execute({
                "pattern": "*.txt",
                "path": str(project_root / ".."),
            })

            assert result.success is False

    def test_glob_within_project_root(self):
        """Test that glob within project root works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "test.txt").write_text("content")

            tool = GlobTool(project_root=str(project_root))
            result = tool.execute({
                "pattern": "*.txt",
                "path": str(project_root),
            })

            assert result.success is True
            assert "test.txt" in result.output

    def test_no_project_root_allows_all(self):
        """Test that without project_root, all paths are allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "test.txt").write_text("content")

            tool = GlobTool()  # No project_root
            result = tool.execute({
                "pattern": "*.txt",
                "path": temp_dir,
            })

            assert result.success is True


class TestGlobToolValidation:
    """Validation tests for GlobTool."""

    def test_missing_pattern(self):
        """Test that missing pattern raises error."""
        tool = GlobTool()
        from claude_code.core.tools.base import ToolValidationError

        with pytest.raises(ToolValidationError):
            tool.execute({})

    def test_empty_pattern(self):
        """Test that empty pattern fails."""
        tool = GlobTool()
        result = tool.execute({"pattern": ""})

        assert result.success is False
        assert "empty" in result.error.lower()

    def test_invalid_path(self):
        """Test that invalid path fails."""
        tool = GlobTool()
        result = tool.execute({
            "pattern": "*.txt",
            "path": "/nonexistent/path/xyz123",
        })

        assert result.success is False
        assert "not found" in result.error.lower() or "not exist" in result.error.lower()

    def test_path_is_file_not_directory(self):
        """Test that path must be a directory."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            tool = GlobTool()
            result = tool.execute({
                "pattern": "*.txt",
                "path": temp_file,
            })

            assert result.success is False
            assert "not a directory" in result.error.lower()
        finally:
            os.unlink(temp_file)

    def test_limit_must_be_positive(self):
        """Test that limit must be positive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "test.txt").write_text("content")

            tool = GlobTool()
            result = tool.execute({
                "pattern": "*.txt",
                "path": temp_dir,
                "limit": -1,
            })

            # Should use default limit instead of negative
            assert result.success is True
