"""
EasyOCR wrapper for desktop automation.

Provides OCR functionality using EasyOCR with preprocessing
to improve recognition accuracy.
"""

import io
from typing import List, Dict, Any, Optional, Tuple

# Lazy imports
_easyocr = None
_np = None
_cv2 = None
_pil_image = None

# Global reader cache (EasyOCR reader is expensive to create)
_readers = {}  # type: Dict[str, Any]


def _get_easyocr():
    global _easyocr
    if _easyocr is None:
        import easyocr
        _easyocr = easyocr
    return _easyocr


def _get_numpy():
    global _np
    if _np is None:
        import numpy as np
        _np = np
    return _np


def _get_cv2():
    global _cv2
    if _cv2 is None:
        import cv2
        _cv2 = cv2
    return _cv2


def _get_pil():
    global _pil_image
    if _pil_image is None:
        from PIL import Image
        _pil_image = Image
    return _pil_image


def get_reader(langs: List[str]) -> Any:
    """
    Get or create EasyOCR reader for specified languages.

    Args:
        langs: List of language codes (e.g., ["en"], ["ch_sim", "en"])

    Returns:
        EasyOCR Reader instance.
    """
    key = ",".join(sorted(langs))
    if key not in _readers:
        easyocr = _get_easyocr()
        _readers[key] = easyocr.Reader(langs, gpu=False)
    return _readers[key]


def preprocess_image(image_bytes: bytes) -> bytes:
    """
    Preprocess image to improve OCR accuracy.

    Applies:
    - Grayscale conversion
    - Contrast enhancement (CLAHE)
    - Noise reduction
    - Sharpening

    Args:
        image_bytes: PNG image data.

    Returns:
        Preprocessed PNG image data.
    """
    np = _get_numpy()
    cv2 = _get_cv2()
    Image = _get_pil()

    # Load image
    img = Image.open(io.BytesIO(image_bytes))
    img_array = np.array(img)

    # Convert to grayscale if color
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)

    # Sharpen
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    sharpened = cv2.filter2D(denoised, -1, kernel)

    # Convert back to PIL and PNG bytes
    result_img = Image.fromarray(sharpened)
    buffer = io.BytesIO()
    result_img.save(buffer, format="PNG")
    return buffer.getvalue()


def ocr_image(
    image_bytes: bytes,
    langs: Optional[List[str]] = None,
    preprocess: bool = True
) -> List[Dict[str, Any]]:
    """
    Perform OCR on image using EasyOCR.

    Args:
        image_bytes: PNG image data.
        langs: Language codes. Default ["en"].
               Use ["ch_sim", "en"] for Chinese + English.
        preprocess: Whether to preprocess image for better accuracy.

    Returns:
        List of dicts with keys: text, x, y, width, height, confidence
    """
    np = _get_numpy()
    Image = _get_pil()

    if langs is None:
        langs = ["en"]

    # Preprocess if requested
    if preprocess:
        try:
            image_bytes = preprocess_image(image_bytes)
        except Exception:
            pass  # Use original if preprocessing fails

    # Load image as numpy array
    img = Image.open(io.BytesIO(image_bytes))
    img_array = np.array(img)

    # Get reader and perform OCR
    reader = get_reader(langs)
    results = reader.readtext(img_array)

    # Convert to standard format
    ocr_results = []
    for bbox, text, confidence in results:
        if not text.strip():
            continue

        # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        x1 = int(min(p[0] for p in bbox))
        y1 = int(min(p[1] for p in bbox))
        x2 = int(max(p[0] for p in bbox))
        y2 = int(max(p[1] for p in bbox))

        ocr_results.append({
            "text": text.strip(),
            "x": x1,
            "y": y1,
            "width": x2 - x1,
            "height": y2 - y1,
            "confidence": int(confidence * 100)
        })

    return ocr_results


# Language code mapping
LANG_MAP = {
    "eng": ["en"],
    "en": ["en"],
    "chi_sim": ["ch_sim", "en"],
    "ch_sim": ["ch_sim", "en"],
    "chinese": ["ch_sim", "en"],
    "chi_tra": ["ch_tra", "en"],
    "ch_tra": ["ch_tra", "en"],
    "jpn": ["ja", "en"],
    "ja": ["ja", "en"],
    "japanese": ["ja", "en"],
    "kor": ["ko", "en"],
    "ko": ["ko", "en"],
    "korean": ["ko", "en"],
}


def normalize_lang(lang: str) -> List[str]:
    """
    Normalize language code to EasyOCR format.

    Args:
        lang: Language code (tesseract or easyocr format).

    Returns:
        List of EasyOCR language codes.
    """
    lang_lower = lang.lower()
    return LANG_MAP.get(lang_lower, [lang_lower])
