"""
Tests for ReadImage tool (T020)

Python 3.8.10 compatible
"""

import pytest
import os
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch

from deep_code.core.tools.base import Tool, ToolCategory, ToolResult, ToolParameter


class TestReadImageTool:
    """Tests for ReadImage tool."""

    def test_tool_properties(self):
        """Test tool basic properties."""
        from deep_code.core.tools.ocr import ReadImageTool

        tool = ReadImageTool()

        assert tool.name == "ReadImage"
        assert "image" in tool.description.lower() or "ocr" in tool.description.lower()
        assert tool.category == ToolCategory.FILE

    def test_tool_parameters(self):
        """Test tool parameters."""
        from deep_code.core.tools.ocr import ReadImageTool

        tool = ReadImageTool()
        params = tool.parameters

        # Should have file_path parameter
        param_names = [p.name for p in params]
        assert "file_path" in param_names

    def test_tool_requires_permission(self):
        """Test that tool requires permission."""
        from deep_code.core.tools.ocr import ReadImageTool

        tool = ReadImageTool()

        assert tool.requires_permission is True

    def test_tool_json_schema(self):
        """Test JSON schema generation."""
        from deep_code.core.tools.ocr import ReadImageTool

        tool = ReadImageTool()
        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "ReadImage"
        assert "file_path" in schema["function"]["parameters"]["properties"]


class TestReadImageToolExecution:
    """Tests for ReadImage tool execution."""

    def test_execute_success(self, tmp_path):
        """Test successful image recognition."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.extensions.ocr.engine import OCREngine
        from deep_code.extensions.ocr.result import OCRResult, TextBlock

        # Create a fake image file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        tool = ReadImageTool()

        # Mock the OCR engine
        mock_result = OCRResult(
            text="Hello World\nTest Text",
            blocks=[
                TextBlock("Hello World", 0.95, [0, 0, 100, 30]),
                TextBlock("Test Text", 0.90, [0, 40, 100, 70]),
            ],
            language="en",
        )

        with patch.object(tool, '_get_ocr_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.recognize.return_value = mock_result
            mock_get_engine.return_value = mock_engine

            result = tool.execute({"file_path": str(test_image)})

        assert result.success is True
        assert "Hello World" in result.output
        assert "Test Text" in result.output

    def test_execute_file_not_found(self):
        """Test execution with non-existent file."""
        from deep_code.core.tools.ocr import ReadImageTool

        tool = ReadImageTool()
        result = tool.execute({"file_path": "/nonexistent/image.png"})

        assert result.success is False
        assert "not found" in result.error.lower() or "not exist" in result.error.lower()

    def test_execute_unsupported_format(self, tmp_path):
        """Test execution with unsupported format."""
        from deep_code.core.tools.ocr import ReadImageTool

        # Create a text file
        test_file = tmp_path / "test.txt"
        test_file.write_text("not an image")

        tool = ReadImageTool()
        result = tool.execute({"file_path": str(test_file)})

        assert result.success is False
        assert "unsupported" in result.error.lower() or "format" in result.error.lower()

    def test_execute_missing_file_path(self):
        """Test execution with missing file_path parameter."""
        from deep_code.core.tools.ocr import ReadImageTool

        tool = ReadImageTool()
        result = tool.execute({})

        assert result.success is False
        assert "file_path" in result.error.lower() or "required" in result.error.lower()

    def test_execute_empty_file_path(self):
        """Test execution with empty file_path."""
        from deep_code.core.tools.ocr import ReadImageTool

        tool = ReadImageTool()
        result = tool.execute({"file_path": ""})

        assert result.success is False

    def test_execute_with_output_format_text(self, tmp_path):
        """Test execution with text output format."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.extensions.ocr.result import OCRResult, TextBlock

        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        tool = ReadImageTool()

        mock_result = OCRResult(
            text="Sample Text",
            blocks=[TextBlock("Sample Text", 0.95, [0, 0, 100, 30])],
            language="en",
        )

        with patch.object(tool, '_get_ocr_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.recognize.return_value = mock_result
            mock_get_engine.return_value = mock_engine

            result = tool.execute({
                "file_path": str(test_image),
                "output_format": "text",
            })

        assert result.success is True
        assert "Sample Text" in result.output

    def test_execute_with_output_format_json(self, tmp_path):
        """Test execution with JSON output format."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.extensions.ocr.result import OCRResult, TextBlock
        import json

        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        tool = ReadImageTool()

        mock_result = OCRResult(
            text="Sample Text",
            blocks=[TextBlock("Sample Text", 0.95, [0, 0, 100, 30])],
            language="en",
        )

        with patch.object(tool, '_get_ocr_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.recognize.return_value = mock_result
            mock_get_engine.return_value = mock_engine

            result = tool.execute({
                "file_path": str(test_image),
                "output_format": "json",
            })

        assert result.success is True
        # Should be valid JSON
        parsed = json.loads(result.output)
        assert "text" in parsed

    def test_execute_empty_ocr_result(self, tmp_path):
        """Test execution when OCR finds no text."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.extensions.ocr.result import OCRResult

        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        tool = ReadImageTool()

        mock_result = OCRResult(text="", blocks=[], language="en")

        with patch.object(tool, '_get_ocr_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.recognize.return_value = mock_result
            mock_get_engine.return_value = mock_engine

            result = tool.execute({"file_path": str(test_image)})

        assert result.success is True
        # Should indicate no text found
        assert result.output == "" or "no text" in result.output.lower()


class TestReadImageToolWithCache:
    """Tests for ReadImage tool with caching."""

    def test_cache_hit(self, tmp_path):
        """Test that cached results are returned."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.core.tools.performance import ToolCache
        from deep_code.extensions.ocr.result import OCRResult, TextBlock

        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        cache = ToolCache()
        tool = ReadImageTool(cache=cache)

        mock_result = OCRResult(
            text="Cached Text",
            blocks=[TextBlock("Cached Text", 0.95, [0, 0, 100, 30])],
            language="en",
        )

        call_count = 0

        def mock_recognize(path):
            nonlocal call_count
            call_count += 1
            return mock_result

        with patch.object(tool, '_get_ocr_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.recognize.side_effect = mock_recognize
            mock_get_engine.return_value = mock_engine

            # First call
            result1 = tool.execute({"file_path": str(test_image)})
            # Second call (should use cache)
            result2 = tool.execute({"file_path": str(test_image)})

        assert result1.success is True
        assert result2.success is True
        assert call_count == 1  # OCR should only be called once

    def test_cache_disabled(self, tmp_path):
        """Test execution with cache disabled."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.extensions.ocr.result import OCRResult, TextBlock

        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        tool = ReadImageTool(cache=None)

        mock_result = OCRResult(
            text="Text",
            blocks=[TextBlock("Text", 0.95, [0, 0, 100, 30])],
            language="en",
        )

        call_count = 0

        def mock_recognize(path):
            nonlocal call_count
            call_count += 1
            return mock_result

        with patch.object(tool, '_get_ocr_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.recognize.side_effect = mock_recognize
            mock_get_engine.return_value = mock_engine

            tool.execute({"file_path": str(test_image)})
            tool.execute({"file_path": str(test_image)})

        assert call_count == 2  # OCR called twice without cache


class TestReadImageToolFormats:
    """Tests for supported image formats."""

    @pytest.mark.parametrize("ext", [".png", ".jpg", ".jpeg", ".bmp", ".tiff"])
    def test_supported_formats(self, tmp_path, ext):
        """Test that supported formats are accepted."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.extensions.ocr.result import OCRResult, TextBlock

        test_image = tmp_path / f"test{ext}"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')  # Fake content

        tool = ReadImageTool()

        mock_result = OCRResult(text="Text", blocks=[], language="en")

        with patch.object(tool, '_get_ocr_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.recognize.return_value = mock_result
            mock_get_engine.return_value = mock_engine

            result = tool.execute({"file_path": str(test_image)})

        # Should not fail due to format
        assert result.success is True or "format" not in result.error.lower()

    @pytest.mark.parametrize("ext", [".txt", ".pdf", ".doc", ".html"])
    def test_unsupported_formats(self, tmp_path, ext):
        """Test that unsupported formats are rejected."""
        from deep_code.core.tools.ocr import ReadImageTool

        test_file = tmp_path / f"test{ext}"
        test_file.write_text("content")

        tool = ReadImageTool()
        result = tool.execute({"file_path": str(test_file)})

        assert result.success is False


class TestReadImageToolMetadata:
    """Tests for result metadata."""

    def test_result_includes_metadata(self, tmp_path):
        """Test that result includes useful metadata."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.extensions.ocr.result import OCRResult, TextBlock

        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        tool = ReadImageTool()

        mock_result = OCRResult(
            text="Text",
            blocks=[TextBlock("Text", 0.95, [0, 0, 100, 30])],
            language="en",
        )

        with patch.object(tool, '_get_ocr_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.recognize.return_value = mock_result
            mock_get_engine.return_value = mock_engine

            result = tool.execute({"file_path": str(test_image)})

        assert result.metadata is not None
        assert "file_path" in result.metadata or "blocks_count" in result.metadata


class TestReadImageToolIntegration:
    """Integration tests for ReadImage tool."""

    def test_tool_registration(self):
        """Test that tool can be registered in registry."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tool = ReadImageTool()

        registry.register(tool)

        assert registry.has("ReadImage")
        assert registry.get("ReadImage") is tool

    def test_tool_in_schema(self):
        """Test that tool appears in registry schema."""
        from deep_code.core.tools.ocr import ReadImageTool
        from deep_code.core.tools.registry import ToolRegistry

        registry = ToolRegistry()
        registry.register(ReadImageTool())

        schemas = registry.get_tools_schema()

        tool_names = [s["function"]["name"] for s in schemas]
        assert "ReadImage" in tool_names
