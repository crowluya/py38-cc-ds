"""
OCR Result data classes for DeepCode

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TextBlock:
    """A single text block detected by OCR."""
    text: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2] or [x1, y1, x2, y2, x3, y3, x4, y4]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox,
        }


@dataclass
class OCRResult:
    """Result of OCR recognition."""
    text: str
    blocks: List[TextBlock]
    language: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "text": self.text,
            "blocks": [b.to_dict() for b in self.blocks],
            "language": self.language,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def format_text(self, include_confidence: bool = False) -> str:
        """
        Format result as plain text.

        Args:
            include_confidence: Include confidence scores

        Returns:
            Formatted text string
        """
        if not self.blocks:
            return self.text

        lines = []
        for block in self.blocks:
            if include_confidence:
                lines.append(f"{block.text} [{block.confidence:.2f}]")
            else:
                lines.append(block.text)

        return "\n".join(lines)

    @property
    def average_confidence(self) -> float:
        """Get average confidence score."""
        if not self.blocks:
            return 0.0
        return sum(b.confidence for b in self.blocks) / len(self.blocks)


def format_result(
    result: OCRResult,
    format_type: str = "text",
) -> str:
    """
    Format OCR result for output.

    Args:
        result: OCR result to format
        format_type: Output format ("text", "json", "detailed")

    Returns:
        Formatted string
    """
    if format_type == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    if format_type == "detailed":
        lines = []
        lines.append(f"Language: {result.language or 'auto'}")
        lines.append(f"Blocks: {len(result.blocks)}")
        lines.append(f"Average Confidence: {result.average_confidence:.2%}")
        lines.append("")
        lines.append("Text:")
        lines.append("-" * 40)
        for block in result.blocks:
            lines.append(f"  {block.text} (conf: {block.confidence:.2%})")
        return "\n".join(lines)

    # Default: plain text
    return result.format_text()
