"""JUnit XML output formatter for CI/CD integration."""

from typing import List
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from pylint_integrator.formatters.base import BaseFormatter
from pylint_integrator.core.results import AnalysisResult, Issue, MessageType


class JUnitFormatter(BaseFormatter):
    """Formatter for JUnit XML output (for CI/CD systems)."""

    def format(self, result: AnalysisResult) -> str:
        """
        Format complete analysis result as JUnit XML.

        Args:
            result: Analysis result to format

        Returns:
            JUnit XML string
        """
        # Create test suite element
        testsuite = Element(
            "testsuite",
            {
                "name": "pylint",
                "tests": str(len(result.issues)),
                "failures": str(result.error_count + result.fatal_count),
                "errors": str(result.fatal_count),
                "time": str(result.execution_time),
            }
        )

        # Add properties
        properties = SubElement(testsuite, "properties")
        self._add_property(properties, "python_version", result.python_version)
        self._add_property(properties, "pylint_version", result.pylint_version)
        self._add_property(properties, "global_score", str(result.global_score or 0))
        self._add_property(properties, "total_issues", str(result.total_issues))

        # Group issues by module
        issues_by_module: dict = {}
        for issue in result.issues:
            module = issue.module or "unknown"
            if module not in issues_by_module:
                issues_by_module[module] = []
            issues_by_module[module].append(issue)

        # Create test cases for each module
        for module, issues in issues_by_module.items():
            testcase = SubElement(
                testsuite,
                "testcase",
                {
                    "name": module,
                    "classname": "pylint.analysis",
                    "time": "0",  # We don't have per-module timing
                }
            )

            # Add failures for error/fatal issues
            error_issues = [i for i in issues if i.type in [MessageType.ERROR, MessageType.FATAL]]
            if error_issues:
                failure = SubElement(testcase, "failure", {
                    "message": f"Found {len(error_issues)} error(s) in {module}"
                })
                failure.text = self._format_issues_for_junit(error_issues)

            # Add errors for fatal issues
            fatal_issues = [i for i in issues if i.type == MessageType.FATAL]
            if fatal_issues:
                error = SubElement(testcase, "error", {
                    "message": f"Found {len(fatal_issues)} fatal issue(s) in {module}"
                })
                error.text = self._format_issues_for_junit(fatal_issues)

            # Add skipped/warning info for warnings (optional)
            warning_issues = [i for i in issues if i.type == MessageType.WARNING]
            if warning_issues and not (error_issues or fatal_issues):
                # Some CI systems treat warnings as skipped
                skipped = SubElement(testcase, "system-out")
                skipped.text = f"Warnings found:\n{self._format_issues_for_junit(warning_issues)}"

        # Pretty print XML
        rough_xml = tostring(testsuite, encoding="unicode")
        reparsed = minidom.parseString(rough_xml)
        return reparsed.toprettyxml(indent="  ")

    def _add_property(self, parent: Element, name: str, value: str) -> None:
        """Add a property element."""
        prop = SubElement(parent, "property", {"name": name, "value": value})

    def _format_issues_for_junit(self, issues: List[Issue]) -> str:
        """Format issues for JUnit output."""
        lines = []
        for issue in issues:
            lines.append(f"{issue.location_str}: {issue.msg_id} - {issue.message}")
            if issue.context:
                lines.append(f"  Context: {issue.context}")
        return "\n".join(lines)

    def format_summary(self, result: AnalysisResult) -> str:
        """Format summary as JUnit XML."""
        return self.format(result)

    def format_issues(self, result: AnalysisResult) -> str:
        """Format issues as JUnit XML."""
        return self.format(result)

    def format_metrics(self, result: AnalysisResult) -> str:
        """Format metrics as JUnit XML."""
        return self.format(result)
