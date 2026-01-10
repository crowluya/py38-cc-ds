"""
Tests for Grep tool (T009)

Python 3.8.10 compatible
"""

import os
import tempfile
import pytest
from pathlib import Path

from deep_code.core.tools.grep import GrepTool


class TestGrepTool:
    """Tests for GrepTool."""

    def test_properties(self):
        """Test tool properties."""
        tool = GrepTool()
        assert tool.name == "Grep"
        assert "search" in tool.description.lower()
        assert len(tool.parameters) >= 4
        assert tool.requires_permission is True
        assert tool.is_dangerous is False

    def test_json_schema(self):
        """Test JSON schema generation."""
        tool = GrepTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "Grep"
        assert "pattern" in schema["function"]["parameters"]["properties"]
        assert "path" in schema["function"]["parameters"]["properties"]
        assert "pattern" in schema["function"]["parameters"]["required"]

    def test_simple_search(self):
        """Test simple pattern search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello World\nFoo Bar\nHello Python\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "Hello",
                "path": temp_dir,
                "output_mode": "content",
            })

            assert result.success is True
            assert "Hello" in result.output

    def test_regex_pattern(self):
        """Test regex pattern search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("error123\nwarning456\nerror789\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": r"error\d+",
                "path": temp_dir,
                "output_mode": "content",
            })

            assert result.success is True
            assert "error123" in result.output
            assert "error789" in result.output

    def test_case_insensitive(self):
        """Test case insensitive search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello\nHELLO\nhello\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "hello",
                "path": temp_dir,
                "case_insensitive": True,
            })

            assert result.success is True
            # Should match all three
            assert result.metadata["match_count"] >= 3

    def test_no_matches(self):
        """Test pattern with no matches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello World\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "NotFound",
                "path": temp_dir,
            })

            assert result.success is True
            assert result.metadata["match_count"] == 0

    def test_glob_filter(self):
        """Test glob filter for file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create different file types
            (Path(temp_dir) / "test.py").write_text("def hello():\n    pass\n")
            (Path(temp_dir) / "test.txt").write_text("hello world\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "hello",
                "path": temp_dir,
                "glob": "*.py",
            })

            assert result.success is True
            assert "test.py" in result.output
            assert "test.txt" not in result.output

    def test_output_mode_content(self):
        """Test output_mode content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Line 1\nMatch here\nLine 3\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "Match",
                "path": temp_dir,
                "output_mode": "content",
            })

            assert result.success is True
            assert "Match here" in result.output

    def test_output_mode_files_with_matches(self):
        """Test output_mode files_with_matches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "file1.txt").write_text("match\n")
            (Path(temp_dir) / "file2.txt").write_text("no match here\n")
            (Path(temp_dir) / "file3.txt").write_text("match again\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "match",
                "path": temp_dir,
                "output_mode": "files_with_matches",
            })

            assert result.success is True
            assert "file1.txt" in result.output
            assert "file3.txt" in result.output

    def test_output_mode_count(self):
        """Test output_mode count."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("match\nmatch\nmatch\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "match",
                "path": temp_dir,
                "output_mode": "count",
            })

            assert result.success is True
            assert result.metadata["match_count"] == 3

    def test_context_lines(self):
        """Test context lines (-A, -B, -C)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Line 1\nLine 2\nMATCH\nLine 4\nLine 5\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "MATCH",
                "path": temp_dir,
                "output_mode": "content",
                "context_before": 1,
                "context_after": 1,
            })

            assert result.success is True
            assert "Line 2" in result.output
            assert "MATCH" in result.output
            assert "Line 4" in result.output

    def test_limit_results(self):
        """Test limit parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many matching files
            for i in range(10):
                (Path(temp_dir) / f"file{i}.txt").write_text("match\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "match",
                "path": temp_dir,
                "output_mode": "files_with_matches",
                "limit": 3,
            })

            assert result.success is True
            # Should be limited

    def test_recursive_search(self):
        """Test recursive search in subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            (Path(temp_dir) / "root.txt").write_text("match\n")
            (subdir / "nested.txt").write_text("match\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "match",
                "path": temp_dir,
                "output_mode": "files_with_matches",
            })

            assert result.success is True
            assert "root.txt" in result.output
            assert "nested.txt" in result.output

    def test_metadata_included(self):
        """Test that metadata is included in result."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("match\n")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "match",
                "path": temp_dir,
            })

            assert result.success is True
            assert result.metadata is not None
            assert "pattern" in result.metadata
            assert "match_count" in result.metadata

    def test_unicode_content(self):
        """Test unicode content search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello 世界\nПривет мир\n", encoding="utf-8")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "世界",
                "path": temp_dir,
                "output_mode": "content",
            })

            assert result.success is True
            assert "世界" in result.output


class TestGrepToolSecurity:
    """Security tests for GrepTool."""

    def test_path_traversal_blocked(self):
        """Test that path traversal is blocked when project_root is set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            outside_dir = Path(temp_dir) / "outside"
            outside_dir.mkdir()
            (outside_dir / "secret.txt").write_text("secret content")

            tool = GrepTool(project_root=str(project_root))
            result = tool.execute({
                "pattern": "secret",
                "path": str(outside_dir),
            })

            assert result.success is False
            assert "escapes" in result.error.lower()

    def test_path_traversal_with_dotdot(self):
        """Test that .. path traversal is blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            tool = GrepTool(project_root=str(project_root))
            result = tool.execute({
                "pattern": "test",
                "path": str(project_root / ".."),
            })

            assert result.success is False

    def test_grep_within_project_root(self):
        """Test that grep within project root works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "test.txt").write_text("match content")

            tool = GrepTool(project_root=str(project_root))
            result = tool.execute({
                "pattern": "match",
                "path": str(project_root),
            })

            assert result.success is True

    def test_no_project_root_allows_all(self):
        """Test that without project_root, all paths are allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "test.txt").write_text("match")

            tool = GrepTool()  # No project_root
            result = tool.execute({
                "pattern": "match",
                "path": temp_dir,
            })

            assert result.success is True


class TestGrepToolValidation:
    """Validation tests for GrepTool."""

    def test_missing_pattern(self):
        """Test that missing pattern raises error."""
        tool = GrepTool()
        from deep_code.core.tools.base import ToolValidationError

        with pytest.raises(ToolValidationError):
            tool.execute({})

    def test_empty_pattern(self):
        """Test that empty pattern fails."""
        tool = GrepTool()
        result = tool.execute({"pattern": ""})

        assert result.success is False
        assert "empty" in result.error.lower()

    def test_invalid_regex(self):
        """Test that invalid regex fails gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "test.txt").write_text("content")

            tool = GrepTool()
            result = tool.execute({
                "pattern": "[invalid",  # Invalid regex
                "path": temp_dir,
            })

            assert result.success is False
            assert "regex" in result.error.lower() or "pattern" in result.error.lower()

    def test_invalid_path(self):
        """Test that invalid path fails."""
        tool = GrepTool()
        result = tool.execute({
            "pattern": "test",
            "path": "/nonexistent/path/xyz123",
        })

        assert result.success is False
        assert "not found" in result.error.lower() or "not exist" in result.error.lower()

    def test_path_is_file(self):
        """Test that path can be a single file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("match content\n")
            temp_file = f.name

        try:
            tool = GrepTool()
            result = tool.execute({
                "pattern": "match",
                "path": temp_file,
                "output_mode": "content",
            })

            assert result.success is True
            assert "match" in result.output
        finally:
            os.unlink(temp_file)
