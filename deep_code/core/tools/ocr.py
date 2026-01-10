"""
ReadImage tool for OCR image recognition (T020)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Image text recognition using PaddleOCR
- Support for PNG, JPG, BMP, TIFF formats
- Result caching integration
- Multiple output formats (text, json)
"""

import json
import os
from typing import Any, Dict, List, Optional

from deep_code.core.tools.base import Tool, ToolCategory, ToolResult, ToolParameter


# Supported image formats
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


class ReadImageTool(Tool):
    """
    Tool for reading text from images using OCR.

    Uses PaddleOCR for text recognition with support for
    Chinese and English text.
    """

    def __init__(
        self,
        cache: Optional[Any] = None,
        ocr_config: Optional[Any] = None,
    ):
        """
        Initialize ReadImage tool.

        Args:
            cache: Optional ToolCache for caching results
            ocr_config: Optional OCRConfig for engine configuration
        """
        self._cache = cache
        self._ocr_config = ocr_config
        self._ocr_engine: Optional[Any] = None

    @property
    def name(self) -> str:
        """Tool name."""
        return "ReadImage"

    @property
    def description(self) -> str:
        """Tool description for LLM."""
        return (
            "Read and extract text from images using OCR (Optical Character Recognition). "
            "Supports PNG, JPG, BMP, TIFF formats. Returns recognized text with optional "
            "confidence scores and bounding box information."
        )

    @property
    def category(self) -> ToolCategory:
        """Tool category."""
        return ToolCategory.FILE

    @property
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters."""
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="Absolute path to the image file to read",
                required=True,
            ),
            ToolParameter(
                name="output_format",
                type="string",
                description="Output format: 'text' (plain text), 'json' (structured with confidence)",
                required=False,
                default="text",
            ),
        ]

    @property
    def requires_permission(self) -> bool:
        """Whether tool requires permission."""
        return True

    def _get_ocr_engine(self) -> Any:
        """
        Get or create OCR engine instance.

        Returns:
            OCREngine instance
        """
        if self._ocr_engine is None:
            from deep_code.extensions.ocr.engine import OCREngine, OCRConfig

            config = self._ocr_config or OCRConfig()
            self._ocr_engine = OCREngine(config)
        return self._ocr_engine

    def _is_supported_format(self, file_path: str) -> bool:
        """
        Check if file format is supported.

        Args:
            file_path: Path to file

        Returns:
            True if format is supported
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in SUPPORTED_FORMATS

    def _generate_cache_key(self, file_path: str, output_format: str) -> str:
        """
        Generate cache key for the request.

        Args:
            file_path: Path to image file
            output_format: Output format

        Returns:
            Cache key string
        """
        # Include file modification time in cache key
        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            mtime = 0
        return f"ReadImage:{file_path}:{mtime}:{output_format}"

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute OCR on image file.

        Args:
            arguments: Tool arguments containing file_path and optional output_format

        Returns:
            ToolResult with recognized text or error
        """
        # Validate file_path parameter
        file_path = arguments.get("file_path")
        if not file_path:
            return ToolResult.error_result(
                tool_name=self.name,
                error="Missing required parameter: file_path",
            )

        if not isinstance(file_path, str) or not file_path.strip():
            return ToolResult.error_result(
                tool_name=self.name,
                error="Invalid file_path: must be a non-empty string",
            )

        file_path = file_path.strip()
        output_format = arguments.get("output_format", "text")

        # Check if file exists
        if not os.path.exists(file_path):
            return ToolResult.error_result(
                tool_name=self.name,
                error=f"File not found: {file_path}",
            )

        # Check if format is supported
        if not self._is_supported_format(file_path):
            ext = os.path.splitext(file_path)[1]
            return ToolResult.error_result(
                tool_name=self.name,
                error=f"Unsupported image format: {ext}. Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}",
            )

        # Check cache
        if self._cache is not None:
            cache_key = self._generate_cache_key(file_path, output_format)
            cached_result = self._cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        # Perform OCR
        try:
            engine = self._get_ocr_engine()
            ocr_result = engine.recognize(file_path)

            # Format output based on requested format
            if output_format == "json":
                output = json.dumps(ocr_result.to_dict(), ensure_ascii=False, indent=2)
            else:
                # Plain text format
                output = ocr_result.text
                if not output:
                    output = ""  # Empty string for no text found

            # Build metadata
            metadata = {
                "file_path": file_path,
                "blocks_count": len(ocr_result.blocks),
                "language": ocr_result.language,
            }
            if ocr_result.blocks:
                metadata["average_confidence"] = ocr_result.average_confidence

            result = ToolResult.success_result(
                tool_name=self.name,
                output=output,
                metadata=metadata,
            )

            # Cache result
            if self._cache is not None:
                cache_key = self._generate_cache_key(file_path, output_format)
                self._cache.set(cache_key, result)

            return result

        except Exception as e:
            return ToolResult.error_result(
                tool_name=self.name,
                error=f"OCR failed: {str(e)}",
            )
