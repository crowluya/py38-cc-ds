"""Base formatter class."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from pylint_integrator.core.results import AnalysisResult


class BaseFormatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def format(self, result: AnalysisResult) -> str:
        """
        Format analysis result into string output.

        Args:
            result: Analysis result to format

        Returns:
            Formatted string output
        """
        pass

    def format_summary(self, result: AnalysisResult) -> str:
        """
        Format summary section.

        Args:
            result: Analysis result

        Returns:
            Formatted summary string
        """
        raise NotImplementedError()

    def format_issues(self, result: AnalysisResult) -> str:
        """
        Format issues section.

        Args:
            result: Analysis result

        Returns:
            Formatted issues string
        """
        raise NotImplementedError()

    def format_metrics(self, result: AnalysisResult) -> str:
        """
        Format metrics section.

        Args:
            result: Analysis result

        Returns:
            Formatted metrics string
        """
        raise NotImplementedError()
