"""
Tests for OCR engine (T019)

Python 3.8.10 compatible
"""

import pytest
import os
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass


class TestOCRResult:
    """Tests for OCR result data class."""

    def test_ocr_result_creation(self):
        """Test creating OCR result."""
        from deep_code.extensions.ocr.result import OCRResult, TextBlock

        block = TextBlock(
            text="Hello World",
            confidence=0.95,
            bbox=[10, 20, 100, 50],
        )
        result = OCRResult(
            text="Hello World",
            blocks=[block],
            language="en",
        )

        assert result.text == "Hello World"
        assert len(result.blocks) == 1
        assert result.blocks[0].confidence == 0.95

    def test_ocr_result_empty(self):
        """Test empty OCR result."""
        from deep_code.extensions.ocr.result import OCRResult

        result = OCRResult(text="", blocks=[], language="")

        assert result.text == ""
        assert len(result.blocks) == 0

    def test_text_block_to_dict(self):
        """Test TextBlock to dict conversion."""
        from deep_code.extensions.ocr.result import TextBlock

        block = TextBlock(
            text="Test",
            confidence=0.9,
            bbox=[0, 0, 100, 50],
        )

        d = block.to_dict()

        assert d["text"] == "Test"
        assert d["confidence"] == 0.9
        assert d["bbox"] == [0, 0, 100, 50]

    def test_ocr_result_to_dict(self):
        """Test OCRResult to dict conversion."""
        from deep_code.extensions.ocr.result import OCRResult, TextBlock

        result = OCRResult(
            text="Hello",
            blocks=[TextBlock("Hello", 0.95, [0, 0, 50, 20])],
            language="en",
        )

        d = result.to_dict()

        assert d["text"] == "Hello"
        assert len(d["blocks"]) == 1
        assert d["language"] == "en"

    def test_ocr_result_format_text(self):
        """Test formatting OCR result as plain text."""
        from deep_code.extensions.ocr.result import OCRResult, TextBlock

        result = OCRResult(
            text="Line 1\nLine 2",
            blocks=[
                TextBlock("Line 1", 0.95, [0, 0, 100, 20]),
                TextBlock("Line 2", 0.90, [0, 25, 100, 45]),
            ],
            language="en",
        )

        formatted = result.format_text()

        assert "Line 1" in formatted
        assert "Line 2" in formatted


class TestOCRConfig:
    """Tests for OCR configuration."""

    def test_config_defaults(self):
        """Test default configuration."""
        from deep_code.extensions.ocr.engine import OCRConfig

        config = OCRConfig()

        assert config.use_gpu is False
        assert config.lang == "ch"
        assert config.use_angle_cls is True

    def test_config_custom(self):
        """Test custom configuration."""
        from deep_code.extensions.ocr.engine import OCRConfig

        config = OCRConfig(
            use_gpu=False,
            lang="en",
            use_angle_cls=False,
            det_model_dir="/path/to/det",
            rec_model_dir="/path/to/rec",
        )

        assert config.lang == "en"
        assert config.use_angle_cls is False
        assert config.det_model_dir == "/path/to/det"

    def test_config_to_dict(self):
        """Test config to dict conversion."""
        from deep_code.extensions.ocr.engine import OCRConfig

        config = OCRConfig(lang="en")
        d = config.to_dict()

        assert d["lang"] == "en"
        assert "use_gpu" in d


class TestOCREngine:
    """Tests for OCR engine."""

    def test_engine_initialization(self):
        """Test engine initialization."""
        from deep_code.extensions.ocr.engine import OCREngine, OCRConfig

        config = OCRConfig()
        engine = OCREngine(config)

        assert engine.config == config
        assert engine._ocr is None  # Lazy loading

    def test_engine_lazy_loading(self):
        """Test that OCR model is loaded lazily."""
        from deep_code.extensions.ocr.engine import OCREngine, OCRConfig

        config = OCRConfig()
        engine = OCREngine(config)

        # Model should not be loaded yet
        assert engine._ocr is None
        assert engine.is_loaded is False

    def test_engine_supported_formats(self):
        """Test supported image formats."""
        from deep_code.extensions.ocr.engine import OCREngine

        formats = OCREngine.SUPPORTED_FORMATS

        assert ".png" in formats
        assert ".jpg" in formats
        assert ".jpeg" in formats
        assert ".bmp" in formats

    def test_engine_is_supported_format(self):
        """Test checking supported formats."""
        from deep_code.extensions.ocr.engine import OCREngine, OCRConfig

        engine = OCREngine(OCRConfig())

        assert engine.is_supported_format("test.png") is True
        assert engine.is_supported_format("test.PNG") is True
        assert engine.is_supported_format("test.jpg") is True
        assert engine.is_supported_format("test.txt") is False
        assert engine.is_supported_format("test.pdf") is False


class TestOCREngineMocked:
    """Tests for OCR engine with mocked PaddleOCR."""

    def test_recognize_image_success(self, tmp_path):
        """Test successful image recognition."""
        from deep_code.extensions.ocr.engine import OCREngine, OCRConfig
        from deep_code.extensions.ocr.result import OCRResult

        # Create a fake image file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        engine = OCREngine(OCRConfig())

        # Mock PaddleOCR
        mock_ocr = Mock()
        mock_ocr.ocr.return_value = [[
            [[[10, 10], [100, 10], [100, 30], [10, 30]], ("Hello World", 0.95)],
            [[[10, 40], [100, 40], [100, 60], [10, 60]], ("Test Text", 0.90)],
        ]]
        engine._ocr = mock_ocr
        engine._loaded = True

        result = engine.recognize(str(test_image))

        assert isinstance(result, OCRResult)
        assert "Hello World" in result.text
        assert "Test Text" in result.text
        assert len(result.blocks) == 2

    def test_recognize_image_empty_result(self, tmp_path):
        """Test recognition with no text found."""
        from deep_code.extensions.ocr.engine import OCREngine, OCRConfig
        from deep_code.extensions.ocr.result import OCRResult

        # Create a fake image file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        engine = OCREngine(OCRConfig())

        # Mock PaddleOCR returning empty
        mock_ocr = Mock()
        mock_ocr.ocr.return_value = [[]]
        engine._ocr = mock_ocr
        engine._loaded = True

        result = engine.recognize(str(test_image))

        assert isinstance(result, OCRResult)
        assert result.text == ""
        assert len(result.blocks) == 0

    def test_recognize_image_none_result(self, tmp_path):
        """Test recognition with None result."""
        from deep_code.extensions.ocr.engine import OCREngine, OCRConfig
        from deep_code.extensions.ocr.result import OCRResult

        # Create a fake image file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')

        engine = OCREngine(OCRConfig())

        # Mock PaddleOCR returning None
        mock_ocr = Mock()
        mock_ocr.ocr.return_value = [None]
        engine._ocr = mock_ocr
        engine._loaded = True

        result = engine.recognize(str(test_image))

        assert isinstance(result, OCRResult)
        assert result.text == ""

    def test_recognize_unsupported_format(self):
        """Test recognition with unsupported format."""
        from deep_code.extensions.ocr.engine import OCREngine, OCRConfig, OCRError

        engine = OCREngine(OCRConfig())

        with pytest.raises(OCRError) as exc_info:
            engine.recognize("/path/to/file.txt")

        assert "unsupported" in str(exc_info.value).lower()

    def test_recognize_file_not_found(self):
        """Test recognition with non-existent file."""
        from deep_code.extensions.ocr.engine import OCREngine, OCRConfig, OCRError

        engine = OCREngine(OCRConfig())
        engine._ocr = Mock()
        engine._loaded = True

        with pytest.raises(OCRError) as exc_info:
            engine.recognize("/nonexistent/image.png")

        assert "not found" in str(exc_info.value).lower() or "exist" in str(exc_info.value).lower()


class TestImageProcessor:
    """Tests for image preprocessing."""

    def test_processor_initialization(self):
        """Test processor initialization."""
        from deep_code.extensions.ocr.processor import ImageProcessor

        processor = ImageProcessor()
        assert processor is not None

    def test_validate_image_path_exists(self, tmp_path):
        """Test validating existing image path."""
        from deep_code.extensions.ocr.processor import ImageProcessor

        # Create a test image file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b'\x89PNG\r\n\x1a\n')  # PNG header

        processor = ImageProcessor()
        # Should not raise
        processor.validate_path(str(test_image))

    def test_validate_image_path_not_exists(self):
        """Test validating non-existent path."""
        from deep_code.extensions.ocr.processor import ImageProcessor, ImageError

        processor = ImageProcessor()

        with pytest.raises(ImageError):
            processor.validate_path("/nonexistent/image.png")

    def test_get_image_info(self, tmp_path):
        """Test getting image info."""
        from deep_code.extensions.ocr.processor import ImageProcessor

        # Create a minimal valid PNG
        test_image = tmp_path / "test.png"
        # Minimal 1x1 PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
            0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
            0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        test_image.write_bytes(png_data)

        processor = ImageProcessor()
        info = processor.get_image_info(str(test_image))

        assert info is not None
        assert "size" in info or "path" in info

    def test_supported_formats(self):
        """Test supported format checking."""
        from deep_code.extensions.ocr.processor import ImageProcessor

        processor = ImageProcessor()

        assert processor.is_supported("image.png") is True
        assert processor.is_supported("image.jpg") is True
        assert processor.is_supported("image.jpeg") is True
        assert processor.is_supported("image.bmp") is True
        assert processor.is_supported("image.tiff") is True
        assert processor.is_supported("document.pdf") is False
        assert processor.is_supported("text.txt") is False


class TestOCRResultFormatter:
    """Tests for OCR result formatting."""

    def test_format_as_plain_text(self):
        """Test formatting as plain text."""
        from deep_code.extensions.ocr.result import OCRResult, TextBlock, format_result

        result = OCRResult(
            text="Hello\nWorld",
            blocks=[
                TextBlock("Hello", 0.95, [0, 0, 50, 20]),
                TextBlock("World", 0.90, [0, 25, 50, 45]),
            ],
            language="en",
        )

        formatted = format_result(result, format_type="text")

        assert "Hello" in formatted
        assert "World" in formatted

    def test_format_as_json(self):
        """Test formatting as JSON."""
        from deep_code.extensions.ocr.result import OCRResult, TextBlock, format_result
        import json

        result = OCRResult(
            text="Test",
            blocks=[TextBlock("Test", 0.95, [0, 0, 50, 20])],
            language="en",
        )

        formatted = format_result(result, format_type="json")
        parsed = json.loads(formatted)

        assert parsed["text"] == "Test"
        assert len(parsed["blocks"]) == 1

    def test_format_with_confidence(self):
        """Test formatting with confidence scores."""
        from deep_code.extensions.ocr.result import OCRResult, TextBlock, format_result

        result = OCRResult(
            text="Test",
            blocks=[TextBlock("Test", 0.95, [0, 0, 50, 20])],
            language="en",
        )

        formatted = format_result(result, format_type="detailed")

        assert "Test" in formatted
        assert "95" in formatted or "0.95" in formatted


class TestOCREngineIntegration:
    """Integration tests for OCR engine (requires PaddleOCR installed)."""

    @pytest.mark.skipif(
        not os.environ.get("TEST_OCR_INTEGRATION"),
        reason="OCR integration tests disabled (set TEST_OCR_INTEGRATION=1 to enable)"
    )
    def test_real_ocr_recognition(self, tmp_path):
        """Test real OCR recognition (requires PaddleOCR)."""
        from deep_code.extensions.ocr.engine import OCREngine, OCRConfig

        # This test only runs when TEST_OCR_INTEGRATION=1
        config = OCRConfig(use_gpu=False, lang="en")
        engine = OCREngine(config)

        # Would need a real test image
        # result = engine.recognize("test_image.png")
        # assert result.text != ""
        pass


class TestOCRModule:
    """Tests for OCR module exports."""

    def test_module_exports(self):
        """Test that module exports are available."""
        from deep_code.extensions.ocr import (
            OCREngine,
            OCRConfig,
            OCRResult,
            OCRError,
        )

        assert OCREngine is not None
        assert OCRConfig is not None
        assert OCRResult is not None
        assert OCRError is not None
