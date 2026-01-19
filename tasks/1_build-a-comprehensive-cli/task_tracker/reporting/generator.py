"""Report generator for task performance reports."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from task_tracker.database import Database
from task_tracker.analytics import MetricsCollector, TaskAnalyzer, TrendAnalyzer
from task_tracker.reporting.formatters import ConsoleFormatter, JSONFormatter


class ReportGenerator:
    """
    Generate comprehensive task performance reports.

    Combines metrics, analytics, and trends to create
    detailed reports with insights and recommendations.
    """

    def __init__(self, database: Database):
        """
        Initialize report generator.

        Args:
            database: Database connection instance
        """
        self.db = database
        self.metrics_collector = MetricsCollector(database)
        self.task_analyzer = TaskAnalyzer(database)
        self.trend_analyzer = TrendAnalyzer(database)
        self.console_formatter = ConsoleFormatter()
        self.json_formatter = JSONFormatter()

    def generate_summary_report(
        self, period: str = "week"
    ) -> str:
        """
        Generate a summary performance report.

        Args:
            period: Time period for the report

        Returns:
            Formatted report string
        """
        # Collect all metrics
        metrics = self.metrics_collector.get_all_metrics(period)
        efficiency = self.task_analyzer.calculate_efficiency_score()
        insights = self.task_analyzer.generate_insights()

        # Build report structure
        report = {
            "title": f"Task Performance Summary Report ({period})",
            "generated_at": datetime.now().isoformat(),
            "period": period,
            "summary": {
                "efficiency_score": efficiency.get("efficiency_score", 0),
                "completion_rate": metrics["completion_rate"]["completion_rate"],
                "total_tasks": metrics["completion_rate"]["total"],
                "completed_tasks": metrics["completion_rate"]["completed"],
            },
            "metrics": metrics,
            "efficiency": efficiency,
            "insights": insights,
        }

        return self.console_formatter.format_summary_report(report)

    def generate_detailed_report(
        self, period: str = "week"
    ) -> str:
        """
        Generate a detailed performance report.

        Args:
            period: Time period for the report

        Returns:
            Formatted detailed report string
        """
        # Collect comprehensive data
        metrics = self.metrics_collector.get_all_metrics(period)
        efficiency = self.task_analyzer.calculate_efficiency_score()
        insights = self.task_analyzer.generate_insights()
        productivity = self.task_analyzer.analyze_peak_productivity_hours()
        day_patterns = self.task_analyzer.analyze_day_of_week_patterns()
        completion_trend = self.trend_analyzer.calculate_completion_trend()
        cycle_time = self.trend_analyzer.analyze_cycle_time_trend()

        # Build report structure
        report = {
            "title": f"Detailed Task Performance Report ({period})",
            "generated_at": datetime.now().isoformat(),
            "period": period,
            "sections": {
                "overview": {
                    "efficiency_score": efficiency.get("efficiency_score", 0),
                    "total_tasks": metrics["completion_rate"]["total"],
                    "completion_rate": metrics["completion_rate"]["completion_rate"],
                    "avg_execution_time": metrics["execution_times"]["mean_minutes"],
                },
                "execution_times": metrics["execution_times"],
                "productivity_patterns": {
                    "peak_hours": productivity["peak_hours"],
                    "day_of_week": day_patterns,
                },
                "trends": {
                    "completion_trend": completion_trend,
                    "cycle_time_trend": cycle_time,
                },
                "distribution": metrics["distribution"],
                "bottlenecks": metrics["bottlenecks"],
                "insights_and_recommendations": insights,
            },
        }

        return self.console_formatter.format_detailed_report(report)

    def generate_trend_report(self, days: int = 30) -> str:
        """
        Generate a trend analysis report.

        Args:
            days: Number of days to analyze

        Returns:
            Formatted trend report string
        """
        completion_trend = self.trend_analyzer.calculate_completion_trend(days)
        velocity_trend = self.trend_analyzer.calculate_velocity_trend(days)
        cycle_time_trend = self.trend_analyzer.analyze_cycle_time_trend(days)
        burndown = self.trend_analyzer.calculate_burndown(days)
        forecast = self.trend_analyzer.forecast_completion()

        # Build report structure
        report = {
            "title": f"Trend Analysis Report (Last {days} days)",
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "sections": {
                "completion_trend": completion_trend,
                "velocity_trend": velocity_trend,
                "cycle_time_trend": cycle_time_trend,
                "burndown": burndown,
                "forecast": forecast,
            },
        }

        return self.console_formatter.format_trend_report(report)

    def generate_insights_report(self) -> str:
        """
        Generate an insights and recommendations report.

        Returns:
            Formatted insights report string
        """
        insights = self.task_analyzer.generate_insights()
        efficiency = self.task_analyzer.calculate_efficiency_score()
        correlations = self.task_analyzer.analyze_task_type_correlations()

        # Build report structure
        report = {
            "title": "Insights and Recommendations Report",
            "generated_at": datetime.now().isoformat(),
            "sections": {
                "efficiency_analysis": efficiency,
                "insights": insights,
                "correlations": correlations,
            },
        }

        return self.console_formatter.format_insights_report(report)

    def export_report_json(
        self, report_type: str = "summary", period: str = "week", output_path: Optional[str] = None
    ) -> str:
        """
        Export report as JSON.

        Args:
            report_type: Type of report ('summary', 'detailed', 'trend', 'insights')
            period: Time period for the report
            output_path: Optional file path to save JSON

        Returns:
            JSON string
        """
        # Generate report data
        if report_type == "summary":
            metrics = self.metrics_collector.get_all_metrics(period)
            efficiency = self.task_analyzer.calculate_efficiency_score()
            insights = self.task_analyzer.generate_insights()

            report = {
                "title": f"Task Performance Summary Report ({period})",
                "generated_at": datetime.now().isoformat(),
                "period": period,
                "summary": {
                    "efficiency_score": efficiency.get("efficiency_score", 0),
                    "completion_rate": metrics["completion_rate"]["completion_rate"],
                    "total_tasks": metrics["completion_rate"]["total"],
                },
                "metrics": metrics,
                "efficiency": efficiency,
                "insights": insights,
            }
        elif report_type == "detailed":
            metrics = self.metrics_collector.get_all_metrics(period)
            efficiency = self.task_analyzer.calculate_efficiency_score()
            insights = self.task_analyzer.generate_insights()

            report = {
                "title": f"Detailed Task Performance Report ({period})",
                "generated_at": datetime.now().isoformat(),
                "metrics": metrics,
                "efficiency": efficiency,
                "insights": insights,
            }
        elif report_type == "trend":
            completion_trend = self.trend_analyzer.calculate_completion_trend()
            velocity_trend = self.trend_analyzer.calculate_velocity_trend()

            report = {
                "title": "Trend Analysis Report",
                "generated_at": datetime.now().isoformat(),
                "completion_trend": completion_trend,
                "velocity_trend": velocity_trend,
            }
        else:  # insights
            insights = self.task_analyzer.generate_insights()
            efficiency = self.task_analyzer.calculate_efficiency_score()

            report = {
                "title": "Insights Report",
                "generated_at": datetime.now().isoformat(),
                "efficiency": efficiency,
                "insights": insights,
            }

        json_str = self.json_formatter.format_report(report)

        if output_path:
            with open(output_path, "w") as f:
                f.write(json_str)

        return json_str

    def generate_comparison_report(
        self, period1: str, period2: str
    ) -> str:
        """
        Generate a comparison report between two periods.

        Args:
            period1: First period ('day', 'week', 'month')
            period2: Second period ('day', 'week', 'month')

        Returns:
            Formatted comparison report string
        """
        comparison = self.task_analyzer.compare_periods(period1, period2)

        # Get metrics for both periods
        metrics1 = self.metrics_collector.get_all_metrics(period1)
        metrics2 = self.metrics_collector.get_all_metrics(period2)

        # Build report structure
        report = {
            "title": f"Period Comparison Report: {period1} vs {period2}",
            "generated_at": datetime.now().isoformat(),
            "comparison": comparison,
            "period1_metrics": metrics1,
            "period2_metrics": metrics2,
        }

        return self.console_formatter.format_comparison_report(report)
