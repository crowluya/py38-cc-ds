"""Tests for result data models."""

import pytest
from datetime import datetime

from pylint_integrator.core.results import (
    Issue,
    Metric,
    ModuleStats,
    AnalysisResult,
    MessageType,
)


class TestIssue:
    """Test Issue class."""

    def test_issue_creation(self):
        """Test creating an issue."""
        issue = Issue(
            msg_id="C0111",
            symbol="missing-docstring",
            message="Missing docstring",
            path="src/module.py",
            line=10,
            column=0,
            type=MessageType.CONVENTION,
        )
        assert issue.msg_id == "C0111"
        assert issue.symbol == "missing-docstring"
        assert issue.type == MessageType.CONVENTION
        assert issue.severity == "info"

    def test_severity_calculation(self):
        """Test severity calculation for different message types."""
        error_issue = Issue(
            msg_id="E001",
            symbol="error",
            message="Error",
            path="file.py",
            line=1,
            column=0,
            type=MessageType.ERROR,
        )
        assert error_issue.severity == "error"

        warning_issue = Issue(
            msg_id="W001",
            symbol="warning",
            message="Warning",
            path="file.py",
            line=1,
            column=0,
            type=MessageType.WARNING,
        )
        assert warning_issue.severity == "warning"

    def test_location_str(self):
        """Test location string formatting."""
        issue = Issue(
            msg_id="C001",
            symbol="test",
            message="Test",
            path="src/module.py",
            line=10,
            column=5,
        )
        assert issue.location_str == "src/module.py:10:5"

    def test_issue_to_dict(self):
        """Test converting issue to dictionary."""
        issue = Issue(
            msg_id="C0111",
            symbol="missing-docstring",
            message="Missing docstring",
            path="src/module.py",
            line=10,
            column=0,
            type=MessageType.CONVENTION,
        )
        data = issue.to_dict()
        assert data["msg_id"] == "C0111"
        assert data["symbol"] == "missing-docstring"
        assert data["type"] == "Convention"

    def test_issue_from_dict(self):
        """Test creating issue from dictionary."""
        data = {
            "msg_id": "C0111",
            "symbol": "missing-docstring",
            "message": "Missing docstring",
            "path": "src/module.py",
            "line": 10,
            "column": 0,
            "type": "convention",
        }
        issue = Issue.from_dict(data)
        assert issue.msg_id == "C0111"
        assert issue.type == MessageType.CONVENTION


class TestMetric:
    """Test Metric class."""

    def test_metric_creation(self):
        """Test creating a metric."""
        metric = Metric(
            name="Total Issues",
            value=100.0,
            description="Total number of issues",
        )
        assert metric.name == "Total Issues"
        assert metric.value == 100.0
        assert metric.description == "Total number of issues"

    def test_metric_change(self):
        """Test metric change calculation."""
        metric = Metric(
            name="Score",
            value=8.0,
            previous_value=7.5,
        )
        assert metric.change == 0.5
        assert metric.percentage_change is not None

    def test_metric_no_previous_value(self):
        """Test metric without previous value."""
        metric = Metric(
            name="Score",
            value=8.0,
        )
        assert metric.change is None
        assert metric.percentage_change is None


class TestModuleStats:
    """Test ModuleStats class."""

    def test_module_stats_creation(self):
        """Test creating module statistics."""
        stats = ModuleStats(
            module="mymodule",
            path="src/mymodule.py",
            error_count=5,
            warning_count=10,
        )
        assert stats.module == "mymodule"
        assert stats.path == "src/mymodule.py"

    def test_total_issues(self):
        """Test total issues calculation."""
        stats = ModuleStats(
            module="mymodule",
            path="src/mymodule.py",
            error=5,
            warning=10,
            convention=3,
        )
        assert stats.total_issues == 18


class TestAnalysisResult:
    """Test AnalysisResult class."""

    def test_analysis_result_creation(self):
        """Test creating analysis result."""
        result = AnalysisResult(
            pylint_version="pylint 3.0.0",
            python_version="3.11.0",
        )
        assert result.pylint_version == "pylint 3.0.0"
        assert result.python_version == "3.11.0"
        assert result.total_issues == 0

    def test_issue_counting(self):
        """Test counting issues by type."""
        result = AnalysisResult()

        # Add issues
        result.issues.append(Issue(
            msg_id="E001",
            symbol="error",
            message="Error",
            path="file.py",
            line=1,
            column=0,
            type=MessageType.ERROR,
        ))
        result.issues.append(Issue(
            msg_id="W001",
            symbol="warning",
            message="Warning",
            path="file.py",
            line=2,
            column=0,
            type=MessageType.WARNING,
        ))

        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.total_issues == 2

    def test_has_errors(self):
        """Test has_errors property."""
        result = AnalysisResult()
        assert not result.has_errors

        result.issues.append(Issue(
            msg_id="E001",
            symbol="error",
            message="Error",
            path="file.py",
            line=1,
            column=0,
            type=MessageType.ERROR,
        ))
        assert result.has_errors

    def test_get_issues_by_type(self):
        """Test filtering issues by type."""
        result = AnalysisResult()

        result.issues.append(Issue(
            msg_id="E001",
            symbol="error",
            message="Error",
            path="file.py",
            line=1,
            column=0,
            type=MessageType.ERROR,
        ))
        result.issues.append(Issue(
            msg_id="W001",
            symbol="warning",
            message="Warning",
            path="file.py",
            line=2,
            column=0,
            type=MessageType.WARNING,
        ))

        errors = result.get_issues_by_type(MessageType.ERROR)
        assert len(errors) == 1
        assert errors[0].type == MessageType.ERROR

    def test_get_summary(self):
        """Test getting result summary."""
        result = AnalysisResult(
            global_score=8.5,
            files_analyzed=10,
            modules_analyzed=5,
        )

        result.issues.append(Issue(
            msg_id="E001",
            symbol="error",
            message="Error",
            path="file.py",
            line=1,
            column=0,
            type=MessageType.ERROR,
        ))

        summary = result.get_summary()
        assert summary["global_score"] == 8.5
        assert summary["total_issues"] == 1
        assert summary["files_analyzed"] == 10

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = AnalysisResult(
            pylint_version="3.0.0",
            python_version="3.11.0",
            global_score=8.5,
        )

        data = result.to_dict()
        assert data["pylint_version"] == "3.0.0"
        assert data["python_version"] == "3.11.0"
        assert data["global_score"] == 8.5
        assert "summary" in data
