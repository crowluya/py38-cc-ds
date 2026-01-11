"""
Windows 7 platform implementation for desktop automation.

Uses PIL.ImageGrab for screenshots (more reliable on Win7),
EasyOCR for OCR, and pyautogui for input control.
"""

import io
from typing import Optional, Tuple, List, Dict, Any

from desktop_mcp.platform_base import PlatformBase, BoundingBox, Point

# Lazy imports to avoid import errors if dependencies missing
_pil_image = None
_image_grab = None
_pyautogui = None


def _get_pil():
    global _pil_image
    if _pil_image is None:
        from PIL import Image
        _pil_image = Image
    return _pil_image


def _get_image_grab():
    global _image_grab
    if _image_grab is None:
        from PIL import ImageGrab
        _image_grab = ImageGrab
    return _image_grab


def _get_pyautogui():
    global _pyautogui
    if _pyautogui is None:
        import pyautogui
        # Disable fail-safe for automation reliability
        pyautogui.FAILSAFE = False
        _pyautogui = pyautogui
    return _pyautogui


class WindowsPlatform(PlatformBase):
    """Windows 7 compatible desktop automation."""

    def screenshot(
        self,
        region: Optional[BoundingBox] = None
    ) -> bytes:
        """Capture screenshot using PIL.ImageGrab (Win7 compatible)."""
        ImageGrab = _get_image_grab()

        if region:
            x, y, width, height = region
            bbox = (x, y, x + width, y + height)
            img = ImageGrab.grab(bbox=bbox)
        else:
            img = ImageGrab.grab()

        # Convert to PNG bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def ocr(
        self,
        image_data: Optional[bytes] = None,
        region: Optional[BoundingBox] = None,
        lang: str = "eng"
    ) -> List[Dict[str, Any]]:
        """Perform OCR using EasyOCR with preprocessing."""
        from desktop_mcp.ocr_easyocr import ocr_image, normalize_lang

        # Get image
        if image_data:
            img_bytes = image_data
        else:
            img_bytes = self.screenshot(region)

        # Normalize language and perform OCR
        langs = normalize_lang(lang)
        return ocr_image(img_bytes, langs=langs, preprocess=True)

    def find_text(
        self,
        text: str,
        region: Optional[BoundingBox] = None,
        lang: str = "eng"
    ) -> Optional[Point]:
        """Find text on screen and return center coordinates."""
        ocr_results = self.ocr(region=region, lang=lang)
        text_lower = text.lower()

        # First try exact word match
        for item in ocr_results:
            if text_lower == item["text"].lower():
                center_x = item["x"] + item["width"] // 2
                center_y = item["y"] + item["height"] // 2
                return (center_x, center_y)

        # Then try substring match by combining adjacent words
        full_text = " ".join(item["text"] for item in ocr_results)
        if text_lower in full_text.lower():
            # Find the first word that contains part of the search text
            for item in ocr_results:
                if item["text"].lower() in text_lower or text_lower in item["text"].lower():
                    center_x = item["x"] + item["width"] // 2
                    center_y = item["y"] + item["height"] // 2
                    return (center_x, center_y)

        return None

    def click(self, x: int, y: int, button: str = "left") -> None:
        """Click at coordinates."""
        pyautogui = _get_pyautogui()
        pyautogui.click(x, y, button=button)

    def double_click(self, x: int, y: int) -> None:
        """Double click at coordinates."""
        pyautogui = _get_pyautogui()
        pyautogui.doubleClick(x, y)

    def move_mouse(self, x: int, y: int) -> None:
        """Move mouse to coordinates."""
        pyautogui = _get_pyautogui()
        pyautogui.moveTo(x, y)

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5
    ) -> None:
        """Drag from start to end coordinates."""
        pyautogui = _get_pyautogui()
        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)

    def type_text(self, text: str, interval: float = 0.0) -> None:
        """Type text string."""
        pyautogui = _get_pyautogui()
        pyautogui.typewrite(text, interval=interval)

    def hotkey(self, *keys: str) -> None:
        """Press keyboard shortcut."""
        pyautogui = _get_pyautogui()
        pyautogui.hotkey(*keys)

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Scroll mouse wheel."""
        pyautogui = _get_pyautogui()
        pyautogui.scroll(clicks, x=x, y=y)

    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        pyautogui = _get_pyautogui()
        return pyautogui.size()

    def get_mouse_position(self) -> Point:
        """Get current mouse position."""
        pyautogui = _get_pyautogui()
        pos = pyautogui.position()
        return (pos.x, pos.y)
