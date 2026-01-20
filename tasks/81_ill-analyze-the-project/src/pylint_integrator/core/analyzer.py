"""
Pylint execution engine and analyzer.

Handles running pylint, capturing output, and processing results.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from pylint_integrator.core.config import Configuration
from pylint_integrator.core.results import (
    AnalysisResult,
    Issue,
    ModuleStats,
    Metric,
    MessageType,
)


class PylintAnalyzer:
    """
    Main analyzer class for running pylint and processing results.
    """

    def __init__(self, config: Configuration):
        """
        Initialize analyzer with configuration.

        Args:
            config: Analysis configuration
        """
        self.config = config
        self._pylint_version: Optional[str] = None

    def _get_pylint_version(self) -> str:
        """Get pylint version."""
        if self._pylint_version is None:
            try:
                result = subprocess.run(
                    ["pylint", "--version"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                # Parse version from output
                for line in result.stdout.split("\n"):
                    if "pylint" in line.lower():
                        self._pylint_version = line.strip()
                        break
                else:
                    self._pylint_version = "unknown"
            except FileNotFoundError:
                self._pylint_version = "not installed"
        return self._pylint_version

    def analyze(self) -> AnalysisResult:
        """
        Run pylint analysis on configured paths.

        Returns:
            AnalysisResult containing all findings
        """
        result = AnalysisResult(
            pylint_version=self._get_pylint_version(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            paths_analyzed=self.config.paths.copy(),
        )

        start_time = time.time()

        try:
            # Validate configuration
            errors = self.config.validate()
            if errors:
                result.success = False
                result.error_message = "; ".join(errors)
                return result

            # Run pylint and capture output
            pylint_output = self._run_pylint()

            # Process output
            if pylint_output:
                self._process_output(pylint_output, result)
            else:
                result.success = False
                result.error_message = "No output from pylint"

            result.execution_time = time.time() - start_time

            # Check if score threshold is met
            if self.config.score_threshold and result.global_score:
                if result.global_score < self.config.score_threshold:
                    result.success = False
                    result.error_message = (
                        f"Score {result.global_score:.2f} below threshold "
                        f"{self.config.score_threshold:.2f}"
                    )

            # Check error/warning flags
            if self.config.fail_on_error and result.has_errors:
                result.success = False
                result.error_message = f"Found {result.error_count} errors"

            if self.config.fail_on_warning and result.warning_count > 0:
                result.success = False
                result.error_message = f"Found {result.warning_count} warnings"

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.execution_time = time.time() - start_time

        return result

    def _run_pylint(self) -> Optional[Dict[str, Any]]:
        """
        Execute pylint and capture JSON output.

        Returns:
            Parsed JSON output or None if execution failed
        """
        # Build pylint command
        cmd = ["pylint", "--output-format=json"]

        # Add configuration file
        if self.config.pylintrc:
            cmd.extend(["--rcfile", self.config.pylintrc])

        # Add ignore patterns
        if self.config.ignore_patterns:
            cmd.extend(["--ignore", ",".join(self.config.ignore_patterns)])

        # Add paths
        cmd.extend(self.config.paths)

        # Execute pylint
        try:
            if self.config.verbose:
                print(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Pylint outputs results to stdout
            if result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    # Pylint might have printed non-JSON output
                    if self.config.verbose:
                        print(f"Pylint output (not JSON): {result.stdout}")
                    return None

            # Check if pylint failed
            if result.returncode not in [0, 1, 2, 4, 8, 16, 32]:
                # These return codes are expected for pylint
                # (bitmask for fatal, error, warning, convention, refactor, info)
                if self.config.verbose:
                    print(f"Pylint stderr: {result.stderr}")
                return None

            return []

        except FileNotFoundError:
            raise RuntimeError("pylint is not installed or not in PATH")
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"Failed to run pylint: {e}")

    def _process_output(self, pylint_output: List[Dict[str, Any]], result: AnalysisResult) -> None:
        """
        Process pylint JSON output and populate result.

        Args:
            pylint_output: Parsed JSON from pylint
            result: AnalysisResult to populate
        """
        # Process each issue
        for item in pylint_output:
            issue = Issue.from_pylint_dict(item)
            result.issues.append(issue)

        # Group issues by module and calculate stats
        module_stats_map: Dict[str, ModuleStats] = {}

        for issue in result.issues:
            module = issue.module or Path(issue.path).stem

            if module not in module_stats_map:
                module_stats_map[module] = ModuleStats(
                    module=module,
                    path=issue.path,
                )

            stats = module_stats_map[module]
            if issue.type == MessageType.FATAL:
                stats.fatal += 1
            elif issue.type == MessageType.ERROR:
                stats.error += 1
            elif issue.type == MessageType.WARNING:
                stats.warning += 1
            elif issue.type == MessageType.CONVENTION:
                stats.convention += 1
            elif issue.type == MessageType.REFACTOR:
                stats.refactor += 1
            elif issue.type == MessageType.INFO:
                stats.info += 1

        result.module_stats = list(module_stats_map.values())
        result.modules_analyzed = len(module_stats_map)

        # Calculate global score (inverse of issue density)
        # Pylint uses 10.0 - (fatal*5 + error*2 + warning + convention/2 + refactor/4 + info/8) / statements * 10
        # Simplified: start at 10 and deduct points
        if result.issues:
            total_penalty = (
                result.fatal_count * 5 +
                result.error_count * 2 +
                result.warning_count +
                result.convention_count * 0.5 +
                result.refactor_count * 0.25 +
                result.info_count * 0.125
            )

            # Estimate statements (rough heuristic: assume 100 if no data)
            estimated_statements = max(100, len(result.issues) * 2)
            score_deduction = min(total_penalty / estimated_statements * 10, 10)
            result.global_score = max(0, 10.0 - score_deduction)
        else:
            result.global_score = 10.0

        # Generate metrics
        result.metrics = [
            Metric(name="Total Issues", value=float(result.total_issues), description="Total number of issues found"),
            Metric(name="Fatal", value=float(result.fatal_count), description="Fatal issues"),
            Metric(name="Errors", value=float(result.error_count), description="Error issues"),
            Metric(name="Warnings", value=float(result.warning_count), description="Warning issues"),
            Metric(name="Conventions", value=float(result.convention_count), description="Convention issues"),
            Metric(name="Refactors", value=float(result.refactor_count), description="Refactor suggestions"),
            Metric(name="Info", value=float(result.info_count), description="Info messages"),
            Metric(name="Modules", value=float(result.modules_analyzed), description="Number of modules analyzed"),
            Metric(name="Score", value=result.global_score or 0.0, description="Global code quality score"),
        ]

    def analyze_with_baseline(self, baseline_results: Optional[AnalysisResult] = None) -> AnalysisResult:
        """
        Run analysis and compare with baseline if provided.

        Args:
            baseline_results: Previous analysis results to compare against

        Returns:
            AnalysisResult with trend information
        """
        result = self.analyze()

        if baseline_results:
            # Add previous values to metrics for trend analysis
            for metric in result.metrics:
                for baseline_metric in baseline_results.metrics:
                    if metric.name == baseline_metric.name:
                        metric.previous_value = baseline_metric.value
                        break

        return result

    def get_files_to_analyze(self) -> List[str]:
        """
        Get list of Python files that will be analyzed.

        Returns:
            List of file paths
        """
        files = []

        for path_str in self.config.paths:
            path = Path(path_str)

            if path.is_file():
                if path.suffix == ".py":
                    files.append(str(path))
            elif path.is_dir():
                if self.config.recursive:
                    files.extend(str(p) for p in path.rglob("*.py"))
                else:
                    files.extend(str(p) for p in path.glob("*.py"))

        # Apply ignore patterns
        filtered_files = []
        for file_path in files:
            should_ignore = False
            for pattern in self.config.ignore_patterns:
                if pattern in file_path:
                    should_ignore = True
                    break

            if not should_ignore:
                filtered_files.append(file_path)

        return filtered_files
