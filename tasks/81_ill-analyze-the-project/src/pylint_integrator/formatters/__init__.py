"""Output formatters for pylint analysis results."""

from pylint_integrator.formatters.base import BaseFormatter
from pylint_integrator.formatters.console import ConsoleFormatter
from pylint_integrator.formatters.json_formatter import JSONFormatter
from pylint_integrator.formatters.html_formatter import HTMLFormatter
from pylint_integrator.formatters.junit_formatter import JUnitFormatter

__all__ = [
    "BaseFormatter",
    "ConsoleFormatter",
    "JSONFormatter",
    "HTMLFormatter",
    "JUnitFormatter",
]


def get_formatter(format_type: str) -> BaseFormatter:
    """
    Get formatter instance for specified format type.

    Args:
        format_type: Type of formatter (console, json, html, junit)

    Returns:
        Formatter instance

    Raises:
        ValueError: If format_type is not supported
    """
    formatters = {
        "console": ConsoleFormatter,
        "json": JSONFormatter,
        "html": HTMLFormatter,
        "junit": JUnitFormatter,
    }

    formatter_class = formatters.get(format_type.lower())
    if formatter_class is None:
        raise ValueError(
            f"Unknown format type: {format_type}. "
            f"Supported types: {', '.join(formatters.keys())}"
        )

    return formatter_class()
