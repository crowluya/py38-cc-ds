"""
Image processor for OCR

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import os
from typing import Any, Dict, List, Optional, Tuple


class ImageError(Exception):
    """Image processing error."""
    pass


class ImageProcessor:
    """
    Image preprocessor for OCR.

    Handles:
    - Path validation
    - Format checking
    - Image info extraction
    """

    SUPPORTED_FORMATS = {
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif",
        ".webp", ".gif",
    }

    def __init__(self):
        """Initialize image processor."""
        pass

    def validate_path(self, path: str) -> None:
        """
        Validate image path exists.

        Args:
            path: Path to image file

        Raises:
            ImageError: If path doesn't exist or is not a file
        """
        if not os.path.exists(path):
            raise ImageError(f"Image file not found: {path}")

        if not os.path.isfile(path):
            raise ImageError(f"Path is not a file: {path}")

    def is_supported(self, path: str) -> bool:
        """
        Check if file format is supported.

        Args:
            path: Path to image file

        Returns:
            True if format is supported
        """
        ext = os.path.splitext(path)[1].lower()
        return ext in self.SUPPORTED_FORMATS

    def get_image_info(self, path: str) -> Dict[str, Any]:
        """
        Get basic image information.

        Args:
            path: Path to image file

        Returns:
            Dictionary with image info
        """
        self.validate_path(path)

        info = {
            "path": path,
            "filename": os.path.basename(path),
            "extension": os.path.splitext(path)[1].lower(),
            "size_bytes": os.path.getsize(path),
        }

        # Try to get image dimensions using PIL if available
        try:
            from PIL import Image
            with Image.open(path) as img:
                info["width"] = img.width
                info["height"] = img.height
                info["mode"] = img.mode
                info["format"] = img.format
        except ImportError:
            pass  # PIL not available
        except Exception:
            pass  # Failed to read image

        return info

    def preprocess(
        self,
        path: str,
        max_size: Optional[int] = None,
    ) -> str:
        """
        Preprocess image for OCR.

        Currently just validates the path. Can be extended to:
        - Resize large images
        - Convert formats
        - Enhance contrast

        Args:
            path: Path to image file
            max_size: Maximum dimension (width or height)

        Returns:
            Path to processed image (may be same as input)
        """
        self.validate_path(path)

        if not self.is_supported(path):
            raise ImageError(f"Unsupported image format: {path}")

        # For now, just return the original path
        # Future: implement resizing, format conversion, etc.
        return path
