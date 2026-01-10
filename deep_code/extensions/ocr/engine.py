"""
OCR Engine for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Uses PaddleOCR for text recognition.
Requires: paddlepaddle==2.4.2, paddleocr==2.6.1.3
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from deep_code.extensions.ocr.result import OCRResult, TextBlock
from deep_code.extensions.ocr.processor import ImageProcessor, ImageError


class OCRError(Exception):
    """OCR-related error."""
    pass


@dataclass
class OCRConfig:
    """Configuration for OCR engine."""
    use_gpu: bool = False
    lang: str = "ch"  # "ch" for Chinese+English, "en" for English only
    use_angle_cls: bool = True  # Use angle classification
    det_model_dir: Optional[str] = None  # Custom detection model path
    rec_model_dir: Optional[str] = None  # Custom recognition model path
    cls_model_dir: Optional[str] = None  # Custom classification model path
    show_log: bool = False  # Show PaddleOCR logs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for PaddleOCR initialization."""
        config = {
            "use_gpu": self.use_gpu,
            "lang": self.lang,
            "use_angle_cls": self.use_angle_cls,
            "show_log": self.show_log,
        }
        if self.det_model_dir:
            config["det_model_dir"] = self.det_model_dir
        if self.rec_model_dir:
            config["rec_model_dir"] = self.rec_model_dir
        if self.cls_model_dir:
            config["cls_model_dir"] = self.cls_model_dir
        return config


class OCREngine:
    """
    OCR Engine using PaddleOCR.

    Features:
    - Lazy model loading (loads on first use)
    - Support for Chinese and English text
    - Configurable GPU/CPU mode
    """

    SUPPORTED_FORMATS = {
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif",
        ".webp", ".gif",
    }

    def __init__(self, config: Optional[OCRConfig] = None):
        """
        Initialize OCR engine.

        Args:
            config: OCR configuration (uses defaults if None)
        """
        self._config = config or OCRConfig()
        self._ocr = None
        self._loaded = False
        self._processor = ImageProcessor()

    @property
    def config(self) -> OCRConfig:
        """Get OCR configuration."""
        return self._config

    @property
    def is_loaded(self) -> bool:
        """Check if OCR model is loaded."""
        return self._loaded

    def _ensure_loaded(self) -> None:
        """
        Ensure OCR model is loaded.

        Raises:
            OCRError: If PaddleOCR is not installed
        """
        if self._loaded:
            return

        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(**self._config.to_dict())
            self._loaded = True
        except ImportError:
            raise OCRError(
                "PaddleOCR is not installed. "
                "Install with: pip install paddlepaddle==2.4.2 paddleocr==2.6.1.3"
            )
        except Exception as e:
            raise OCRError(f"Failed to initialize PaddleOCR: {str(e)}")

    def is_supported_format(self, path: str) -> bool:
        """
        Check if file format is supported.

        Args:
            path: Path to image file

        Returns:
            True if format is supported
        """
        ext = os.path.splitext(path)[1].lower()
        return ext in self.SUPPORTED_FORMATS

    def recognize(
        self,
        image_path: str,
        cls: bool = True,
    ) -> OCRResult:
        """
        Recognize text in an image.

        Args:
            image_path: Path to image file
            cls: Use angle classification

        Returns:
            OCRResult with recognized text

        Raises:
            OCRError: If recognition fails
        """
        # Validate format
        if not self.is_supported_format(image_path):
            ext = os.path.splitext(image_path)[1]
            raise OCRError(f"Unsupported image format: {ext}")

        # Validate file exists
        if not os.path.exists(image_path):
            raise OCRError(f"Image file not found: {image_path}")

        # Ensure model is loaded
        self._ensure_loaded()

        try:
            # Run OCR
            result = self._ocr.ocr(image_path, cls=cls)

            # Parse result
            return self._parse_result(result)

        except OCRError:
            raise
        except Exception as e:
            raise OCRError(f"OCR recognition failed: {str(e)}")

    def _parse_result(self, raw_result: Any) -> OCRResult:
        """
        Parse PaddleOCR result into OCRResult.

        Args:
            raw_result: Raw result from PaddleOCR

        Returns:
            Parsed OCRResult
        """
        blocks = []
        texts = []

        # PaddleOCR returns list of pages, each page is list of lines
        if raw_result and len(raw_result) > 0:
            page_result = raw_result[0]

            if page_result:
                for line in page_result:
                    if line and len(line) >= 2:
                        # line[0] is bbox (4 points), line[1] is (text, confidence)
                        bbox_points = line[0]
                        text_info = line[1]

                        if isinstance(text_info, tuple) and len(text_info) >= 2:
                            text = text_info[0]
                            confidence = float(text_info[1])

                            # Convert 4-point bbox to simple bbox
                            bbox = self._convert_bbox(bbox_points)

                            blocks.append(TextBlock(
                                text=text,
                                confidence=confidence,
                                bbox=bbox,
                            ))
                            texts.append(text)

        full_text = "\n".join(texts)

        return OCRResult(
            text=full_text,
            blocks=blocks,
            language=self._config.lang,
        )

    def _convert_bbox(self, points: List[List[float]]) -> List[int]:
        """
        Convert 4-point bbox to [x1, y1, x2, y2] format.

        Args:
            points: List of 4 points [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]

        Returns:
            [x_min, y_min, x_max, y_max]
        """
        if not points or len(points) < 4:
            return [0, 0, 0, 0]

        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]

        return [
            int(min(x_coords)),
            int(min(y_coords)),
            int(max(x_coords)),
            int(max(y_coords)),
        ]

    def unload(self) -> None:
        """Unload OCR model to free memory."""
        self._ocr = None
        self._loaded = False


# Singleton instance for convenience
_default_engine: Optional[OCREngine] = None


def get_default_engine(config: Optional[OCRConfig] = None) -> OCREngine:
    """
    Get the default OCR engine instance.

    Args:
        config: Configuration (only used if creating new instance)

    Returns:
        OCREngine instance
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = OCREngine(config)
    return _default_engine


def recognize_image(image_path: str) -> OCRResult:
    """
    Convenience function to recognize text in an image.

    Args:
        image_path: Path to image file

    Returns:
        OCRResult with recognized text
    """
    engine = get_default_engine()
    return engine.recognize(image_path)
