"""Factory for creating exporters."""

from typing import Optional

from .base import BaseExporter
from .json_exporter import JSONExporter
from .html_exporter import HTMLExporter
from .text_exporter import TextExporter
from .csv_exporter import CSVExporter
from .markdown_exporter import MarkdownExporter
from ..models import AnalysisResult


def export_report(
    result: AnalysisResult,
    format: str = "text",
    output_path: Optional[str] = None,
    config=None
) -> str:
    """Export analysis result in specified format.

    Args:
        result: Analysis result to export
        format: Export format (json, html, text, csv, markdown)
        output_path: Optional file path to write to
        config: Export configuration

    Returns:
        Exported report as string (or file path if written to file)

    Raises:
        ValueError: If format is not supported
    """
    exporter = create_exporter(format, config)
    return exporter.export(result, output_path)


def create_exporter(format: str, config=None) -> BaseExporter:
    """Create exporter instance for specified format.

    Args:
        format: Export format name
        config: Export configuration

    Returns:
        Exporter instance

    Raises:
        ValueError: If format is not supported
    """
    format = format.lower()

    exporters = {
        "json": JSONExporter,
        "html": HTMLExporter,
        "text": TextExporter,
        "txt": TextExporter,
        "csv": CSVExporter,
        "markdown": MarkdownExporter,
        "md": MarkdownExporter,
    }

    if format not in exporters:
        raise ValueError(
            f"Unsupported export format: {format}. "
            f"Supported formats: {', '.join(exporters.keys())}"
        )

    exporter_class = exporters[format]
    return exporter_class(config)
