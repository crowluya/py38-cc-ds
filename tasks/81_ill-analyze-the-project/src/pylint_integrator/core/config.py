"""
Configuration management for pylint integrator.

Handles loading, validation, and management of pylint configurations
from multiple sources (files, CLI args, environment variables).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os
import tomli
import tomli_w


@dataclass
class Configuration:
    """Configuration for pylint analysis."""

    # Directories and files to analyze
    paths: List[str] = field(default_factory=list)

    # Pylint configuration file paths
    config_file: Optional[str] = None

    # Output configuration
    output_format: str = "console"  # console, json, html, junit
    output_file: Optional[str] = None

    # Analysis options
    recursive: bool = True
    ignore_patterns: List[str] = field(default_factory=lambda: ["*.pyc", "__pycache__", ".git"])
    include_tests: bool = True

    # Pylint-specific options
    pylintrc: Optional[str] = None
    pylintrc_override: Dict[str, Any] = field(default_factory=dict)

    # Reporting options
    score_threshold: Optional[float] = None  # Fail if score below this
    fail_on_error: bool = False
    fail_on_warning: bool = False

    # Output customization
    verbose: bool = False
    quiet: bool = False
    show_context: bool = True
    max_issues_per_file: Optional[int] = None

    # Comparison and trending
    baseline_file: Optional[str] = None
    compare_with_baseline: bool = False

    # CI/CD integration
    ci_mode: bool = False
    github_annotations: bool = False

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.output_format not in ["console", "json", "html", "junit"]:
            raise ValueError(
                f"Invalid output format: {self.output_format}. "
                "Must be one of: console, json, html, junit"
            )

        if self.score_threshold is not None and not 0 <= self.score_threshold <= 10:
            raise ValueError("score_threshold must be between 0 and 10")

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "Configuration":
        """
        Load configuration from a TOML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration instance
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "rb") as f:
            data = tomli.load(f)

        config_dict = data.get("tool", {}).get("pylint-integrator", {})
        return cls(**config_dict)

    @classmethod
    def from_pyproject_toml(cls, project_root: Optional[Union[str, Path]] = None) -> "Configuration":
        """
        Load configuration from pyproject.toml in the project root.

        Args:
            project_root: Root directory of the project. If None, uses current directory.

        Returns:
            Configuration instance
        """
        if project_root is None:
            project_root = Path.cwd()
        else:
            project_root = Path(project_root)

        pyproject_path = project_root / "pyproject.toml"
        if not pyproject_path.exists():
            return cls()

        with open(pyproject_path, "rb") as f:
            data = tomli.load(f)

        config_dict = data.get("tool", {}).get("pylint-integrator", {})
        return cls(**config_dict)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Configuration":
        """
        Create configuration from dictionary.

        Args:
            config_dict: Dictionary containing configuration values

        Returns:
            Configuration instance
        """
        return cls(**config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "paths": self.paths,
            "config_file": self.config_file,
            "output_format": self.output_format,
            "output_file": self.output_file,
            "recursive": self.recursive,
            "ignore_patterns": self.ignore_patterns,
            "include_tests": self.include_tests,
            "pylintrc": self.pylintrc,
            "pylintrc_override": self.pylintrc_override,
            "score_threshold": self.score_threshold,
            "fail_on_error": self.fail_on_error,
            "fail_on_warning": self.fail_on_warning,
            "verbose": self.verbose,
            "quiet": self.quiet,
            "show_context": self.show_context,
            "max_issues_per_file": self.max_issues_per_file,
            "baseline_file": self.baseline_file,
            "compare_with_baseline": self.compare_with_baseline,
            "ci_mode": self.ci_mode,
            "github_annotations": self.github_annotations,
        }

    def merge_with(self, other: "Configuration") -> "Configuration":
        """
        Merge this configuration with another, with other taking precedence.

        Args:
            other: Configuration to merge with

        Returns:
            New merged Configuration instance
        """
        merged_dict = self.to_dict()
        other_dict = other.to_dict()

        for key, value in other_dict.items():
            if value is not None:
                if isinstance(value, list) and key in merged_dict:
                    # Merge lists
                    merged_dict[key].extend(value)
                elif isinstance(value, dict) and key in merged_dict:
                    # Merge dictionaries
                    merged_dict[key].update(value)
                else:
                    # Override with other's value
                    merged_dict[key] = value

        return Configuration.from_dict(merged_dict)

    def get_pylint_args(self) -> List[str]:
        """
        Convert configuration to pylint command-line arguments.

        Returns:
            List of pylint command-line arguments
        """
        args = []

        # Add output format
        if self.output_format == "json":
            args.extend(["--output-format=json"])

        # Add configuration file
        if self.pylintrc:
            args.extend(["--rcfile", self.pylintrc])

        # Add ignore patterns
        if self.ignore_patterns:
            args.extend(["--ignore", ",".join(self.ignore_patterns)])

        # Add paths
        args.extend(self.paths)

        return args

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.paths:
            errors.append("No paths specified for analysis")

        for path in self.paths:
            if not Path(path).exists():
                errors.append(f"Path does not exist: {path}")

        if self.output_file:
            output_dir = Path(self.output_file).parent
            if not output_dir.exists():
                try:
                    output_dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    errors.append(f"Cannot create output directory: {e}")

        if self.baseline_file and not Path(self.baseline_file).exists():
            errors.append(f"Baseline file does not exist: {self.baseline_file}")

        return errors
