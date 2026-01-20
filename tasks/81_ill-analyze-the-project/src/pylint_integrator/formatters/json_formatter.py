"""JSON output formatter."""

import json
from typing import Any, Dict

from pylint_integrator.formatters.base import BaseFormatter
from pylint_integrator.core.results import AnalysisResult


class JSONFormatter(BaseFormatter):
    """Formatter for JSON output."""

    def __init__(self, pretty: bool = True):
        """
        Initialize JSON formatter.

        Args:
            pretty: Whether to pretty-print JSON with indentation
        """
        self.pretty = pretty

    def format(self, result: AnalysisResult) -> str:
        """
        Format complete analysis result as JSON.

        Args:
            result: Analysis result to format

        Returns:
            JSON string
        """
        data = result.to_dict()

        if self.pretty:
            return json.dumps(data, indent=2, default=str)
        else:
            return json.dumps(data, default=str)

    def format_summary(self, result: AnalysisResult) -> str:
        """Format only summary as JSON."""
        summary = result.get_summary()
        return json.dumps(summary, indent=2 if self.pretty else None, default=str)

    def format_issues(self, result: AnalysisResult) -> str:
        """Format only issues as JSON."""
        issues = [issue.to_dict() for issue in result.issues]
        return json.dumps(issues, indent=2 if self.pretty else None, default=str)

    def format_metrics(self, result: AnalysisResult) -> str:
        """Format only metrics as JSON."""
        metrics = [metric.to_dict() for metric in result.metrics]
        return json.dumps(metrics, indent=2 if self.pretty else None, default=str)
