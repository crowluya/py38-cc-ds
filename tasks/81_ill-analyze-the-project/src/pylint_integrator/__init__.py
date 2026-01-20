"""
Pylint Integrator - Advanced pylint integration tool for Python code quality analysis.

This package provides a comprehensive wrapper around pylint with enhanced reporting,
configuration management, and CI/CD integration capabilities.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from pylint_integrator.core.analyzer import PylintAnalyzer
from pylint_integrator.core.config import Configuration
from pylint_integrator.core.results import AnalysisResult

__all__ = [
    "PylintAnalyzer",
    "Configuration",
    "AnalysisResult",
    "__version__",
]
