"""Base exporter interface."""

from abc import ABC, abstractmethod
from typing import Optional

from ..models import AnalysisResult


class BaseExporter(ABC):
    """Abstract base class for report exporters."""

    def __init__(self, config=None):
        """Initialize exporter.

        Args:
            config: Export configuration
        """
        self.config = config

    @abstractmethod
    def export(self, result: AnalysisResult, output_path: Optional[str] = None) -> str:
        """Export analysis result.

        Args:
            result: Analysis result to export
            output_path: Optional file path to write to

        Returns:
            Exported report as string (or file path if written to file)
        """
        pass

    def _filter_anomalies(self, result: AnalysisResult, min_severity: Optional[float] = None):
        """Filter anomalies by minimum severity.

        Args:
            result: Analysis result
            min_severity: Minimum severity threshold

        Returns:
            Filtered list of anomalies
        """
        if min_severity is None:
            return result.anomalies
        return [a for a in result.anomalies if a.severity >= min_severity]
