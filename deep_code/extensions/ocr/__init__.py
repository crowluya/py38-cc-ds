"""
OCR module for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides OCR (Optical Character Recognition) functionality using PaddleOCR.

Requirements:
- paddlepaddle==2.4.2
- paddleocr==2.6.1.3
"""

from deep_code.extensions.ocr.engine import (
    OCREngine,
    OCRConfig,
    OCRError,
    get_default_engine,
    recognize_image,
)
from deep_code.extensions.ocr.result import (
    OCRResult,
    TextBlock,
    format_result,
)
from deep_code.extensions.ocr.processor import (
    ImageProcessor,
    ImageError,
)

__all__ = [
    # Engine
    "OCREngine",
    "OCRConfig",
    "OCRError",
    "get_default_engine",
    "recognize_image",
    # Result
    "OCRResult",
    "TextBlock",
    "format_result",
    # Processor
    "ImageProcessor",
    "ImageError",
]
