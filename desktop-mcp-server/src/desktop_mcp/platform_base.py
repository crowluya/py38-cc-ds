"""
Platform abstraction layer for desktop automation.

Provides a unified interface for screenshot, OCR, and input control
across Windows 7 and macOS.
"""

import sys
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict, Any

# Type aliases for Python 3.8 compatibility
BoundingBox = Tuple[int, int, int, int]  # (x, y, width, height)
Point = Tuple[int, int]  # (x, y)


class PlatformBase(ABC):
    """Abstract base class for platform-specific implementations."""

    @abstractmethod
    def screenshot(
        self,
        region: Optional[BoundingBox] = None
    ) -> bytes:
        """
        Capture screenshot of screen or region.

        Args:
            region: Optional (x, y, width, height) tuple for partial capture.
                   If None, captures full screen.

        Returns:
            PNG image data as bytes.
        """
        pass

    @abstractmethod
    def ocr(
        self,
        image_data: Optional[bytes] = None,
        region: Optional[BoundingBox] = None,
        lang: str = "eng"
    ) -> List[Dict[str, Any]]:
        """
        Perform OCR on screen or image.

        Args:
            image_data: Optional PNG image bytes. If None, captures screen.
            region: Optional region to capture if image_data is None.
            lang: OCR language code (e.g., "eng", "chi_sim").

        Returns:
            List of dicts with keys: text, x, y, width, height, confidence
        """
        pass

    @abstractmethod
    def find_text(
        self,
        text: str,
        region: Optional[BoundingBox] = None,
        lang: str = "eng"
    ) -> Optional[Point]:
        """
        Find text on screen and return center coordinates.

        Args:
            text: Text to find (case-insensitive substring match).
            region: Optional region to search.
            lang: OCR language code.

        Returns:
            (x, y) center coordinates if found, None otherwise.
        """
        pass

    @abstractmethod
    def click(self, x: int, y: int, button: str = "left") -> None:
        """
        Click at coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.
            button: "left", "right", or "middle".
        """
        pass

    @abstractmethod
    def double_click(self, x: int, y: int) -> None:
        """Double click at coordinates."""
        pass

    @abstractmethod
    def move_mouse(self, x: int, y: int) -> None:
        """Move mouse to coordinates."""
        pass

    @abstractmethod
    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5
    ) -> None:
        """Drag from start to end coordinates."""
        pass

    @abstractmethod
    def type_text(self, text: str, interval: float = 0.0) -> None:
        """
        Type text string.

        Args:
            text: Text to type.
            interval: Delay between keystrokes in seconds.
        """
        pass

    @abstractmethod
    def hotkey(self, *keys: str) -> None:
        """
        Press keyboard shortcut.

        Args:
            keys: Key names (e.g., "ctrl", "c" for Ctrl+C).
        """
        pass

    @abstractmethod
    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """
        Scroll mouse wheel.

        Args:
            clicks: Number of scroll clicks (positive=up, negative=down).
            x: Optional X coordinate to scroll at.
            y: Optional Y coordinate to scroll at.
        """
        pass

    @abstractmethod
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions as (width, height)."""
        pass

    @abstractmethod
    def get_mouse_position(self) -> Point:
        """Get current mouse position as (x, y)."""
        pass


def get_platform() -> PlatformBase:
    """
    Factory function to get platform-specific implementation.

    Returns:
        PlatformBase implementation for current OS.

    Raises:
        NotImplementedError: If platform is not supported.
    """
    if sys.platform == "win32":
        from desktop_mcp.platform_windows import WindowsPlatform
        return WindowsPlatform()
    elif sys.platform == "darwin":
        from desktop_mcp.platform_macos import MacOSPlatform
        return MacOSPlatform()
    else:
        raise NotImplementedError(f"Platform {sys.platform} not supported")
