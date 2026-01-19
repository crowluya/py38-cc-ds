"""Formatters for different output formats."""

import json
import csv
from typing import Dict, List, Any
from io import StringIO

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class ConsoleFormatter:
    """Format reports for console output."""

    def __init__(self):
        """Initialize console formatter."""
        self.use_color = COLORAMA_AVAILABLE
        self.use_tables = TABULATE_AVAILABLE

    def _colorize(self, text: str, color: str = "white") -> str:
        """Add color to text if colorama is available."""
        if not self.use_color:
            return text

        color_map = {
            "red": Fore.RED,
            "green": Fore.GREEN,
            "yellow": Fore.YELLOW,
            "blue": Fore.BLUE,
            "cyan": Fore.CYAN,
            "magenta": Fore.MAGENTA,
            "white": Fore.WHITE,
        }

        return f"{color_map.get(color, Fore.WHITE)}{text}{Style.RESET_ALL}"

    def format_summary_report(self, report: Dict[str, Any]) -> str:
        """Format summary report for console."""
        lines = []
        lines.append("=" * 70)
        lines.append(self._colorize(f"  {report['title']}", "cyan"))
        lines.append(f"  Generated: {report['generated_at']}")
        lines.append("=" * 70)
        lines.append("")

        # Summary section
        summary = report["summary"]
        lines.append(self._colorize("SUMMARY", "yellow"))
        lines.append("-" * 70)

        eff_score = summary["efficiency_score"]
        eff_color = "green" if eff_score >= 70 else "yellow" if eff_score >= 50 else "red"

        lines.append(f"  Efficiency Score: {self._colorize(f'{eff_score}%', eff_color)}")
        lines.append(f"  Total Tasks: {summary['total_tasks']}")
        lines.append(f"  Completed Tasks: {summary['completed_tasks']}")
        lines.append(f"  Completion Rate: {summary['completion_rate']}%")
        lines.append("")

        # Key metrics
        metrics = report["metrics"]
        lines.append(self._colorize("KEY METRICS", "yellow"))
        lines.append("-" * 70)

        exec_time = metrics["execution_times"]
        lines.append(f"  Avg Execution Time: {exec_time['mean_minutes']} minutes")
        lines.append(f"  Median Execution Time: {exec_time['median_minutes']} minutes")

        productivity = metrics["productivity"]
        lines.append(f"  Avg Tasks/Day: {productivity['avg_tasks_per_day']}")

        lines.append("")

        # Top insights
        insights = report["insights"]
        if insights:
            lines.append(self._colorize("KEY INSIGHTS", "yellow"))
            lines.append("-" * 70)
            for insight in insights[:5]:
                color = "green" if insight["type"] == "positive" else "red"
                lines.append(f"  • {self._colorize(insight['title'], color)}")
                lines.append(f"    {insight['message']}")
                lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def format_detailed_report(self, report: Dict[str, Any]) -> str:
        """Format detailed report for console."""
        lines = []
        lines.append("=" * 70)
        lines.append(self._colorize(f"  {report['title']}", "cyan"))
        lines.append(f"  Generated: {report['generated_at']}")
        lines.append("=" * 70)
        lines.append("")

        # Overview
        overview = report["sections"]["overview"]
        lines.append(self._colorize("OVERVIEW", "yellow"))
        lines.append("-" * 70)
        lines.append(f"  Efficiency Score: {overview['efficiency_score']}%")
        lines.append(f"  Total Tasks: {overview['total_tasks']}")
        lines.append(f"  Completion Rate: {overview['completion_rate']}%")
        lines.append(f"  Avg Execution Time: {overview['avg_execution_time']} minutes")
        lines.append("")

        # Distribution
        distribution = report["sections"]["distribution"]
        lines.append(self._colorize("TASK DISTRIBUTION", "yellow"))
        lines.append("-" * 70)
        lines.append(f"  By Status: {distribution['by_status']}")
        lines.append(f"  By Priority: {distribution['by_priority']}")
        lines.append("")

        # Productivity patterns
        patterns = report["sections"]["productivity_patterns"]
        lines.append(self._colorize("PRODUCTIVITY PATTERNS", "yellow"))
        lines.append("-" * 70)
        if patterns["peak_hours"]:
            lines.append(f"  Peak Hours: {[h['time_range'] for h in patterns['peak_hours']]}")
        lines.append("")

        # Bottlenecks
        bottlenecks = report["sections"]["bottlenecks"]
        if bottlenecks:
            lines.append(self._colorize("BOTTLENECKS", "red"))
            lines.append("-" * 70)
            for b in bottlenecks[:5]:
                lines.append(f"  • {b['title']} ({b['type']})")
            lines.append("")

        # Insights
        insights = report["sections"]["insights_and_recommendations"]
        if insights:
            lines.append(self._colorize("INSIGHTS & RECOMMENDATIONS", "yellow"))
            lines.append("-" * 70)
            for insight in insights[:5]:
                color = "green" if insight["type"] == "positive" else "red"
                lines.append(f"  • {self._colorize(insight['title'], color)}")
                lines.append(f"    {insight['message']}")
                lines.append(f"    → {insight['recommendation']}")
                lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def format_trend_report(self, report: Dict[str, Any]) -> str:
        """Format trend report for console."""
        lines = []
        lines.append("=" * 70)
        lines.append(self._colorize(f"  {report['title']}", "cyan"))
        lines.append(f"  Generated: {report['generated_at']}")
        lines.append("=" * 70)
        lines.append("")

        # Completion trend
        comp_trend = report["sections"]["completion_trend"]
        lines.append(self._colorize("COMPLETION TREND", "yellow"))
        lines.append("-" * 70)
        lines.append(f"  Total Completed: {comp_trend['total_completed']}")
        lines.append(f"  Trend: {comp_trend['trend'].upper()}")
        lines.append(f"  Avg/Day: {comp_trend['avg_per_day']}")
        lines.append("")

        # Velocity trend
        vel_trend = report["sections"]["velocity_trend"]
        lines.append(self._colorize("VELOCITY TREND", "yellow"))
        lines.append("-" * 70)
        lines.append(f"  Current Velocity (7-day): {vel_trend['current_velocity']} tasks")
        lines.append("")

        # Forecast
        forecast = report["sections"]["forecast"]
        lines.append(self._colorize("FORECAST", "yellow"))
        lines.append("-" * 70)
        lines.append(f"  Current Pending: {forecast['current_pending']} tasks")
        lines.append(f"  Projected Completions (7 days): {forecast['projected_completions']}")
        if forecast.get("clearance_days"):
            lines.append(f"  Days to Clear: {forecast['clearance_days']}")
        lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def format_insights_report(self, report: Dict[str, Any]) -> str:
        """Format insights report for console."""
        lines = []
        lines.append("=" * 70)
        lines.append(self._colorize(f"  {report['title']}", "cyan"))
        lines.append(f"  Generated: {report['generated_at']}")
        lines.append("=" * 70)
        lines.append("")

        # Efficiency
        efficiency = report["sections"]["efficiency_analysis"]
        lines.append(self._colorize("EFFICIENCY ANALYSIS", "yellow"))
        lines.append("-" * 70)
        lines.append(f"  Overall Score: {efficiency['efficiency_score']}%")
        lines.append(f"  On-Time Rate: {efficiency['on_time_completion_rate']}%")
        lines.append(f"  Completion Rate: {efficiency['overall_completion_rate']}%")
        lines.append(f"  Estimate Accuracy: {efficiency['estimate_accuracy']}%")
        lines.append("")

        # Insights
        insights = report["sections"]["insights"]
        if insights:
            lines.append(self._colorize("INSIGHTS", "yellow"))
            lines.append("-" * 70)
            for insight in insights:
                color = "green" if insight["type"] == "positive" else "red"
                lines.append(f"  • {self._colorize(insight['title'], color)}")
                lines.append(f"    {insight['message']}")
                lines.append(f"    → {insight['recommendation']}")
                lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def format_comparison_report(self, report: Dict[str, Any]) -> str:
        """Format comparison report for console."""
        lines = []
        lines.append("=" * 70)
        lines.append(self._colorize(f"  {report['title']}", "cyan"))
        lines.append(f"  Generated: {report['generated_at']}")
        lines.append("=" * 70)
        lines.append("")

        comp = report["comparison"]
        lines.append(self._colorize("PERIOD COMPARISON", "yellow"))
        lines.append("-" * 70)

        p1 = comp["period1"]
        p2 = comp["period2"]

        lines.append(f"  {p1['name'].upper()}:")
        lines.append(f"    Total: {p1['total']} | Completed: {p1['completed']} | Rate: {p1['completion_rate']}%")
        lines.append(f"  {p2['name'].upper()}:")
        lines.append(f"    Total: {p2['total']} | Completed: {p2['completed']} | Rate: {p2['completion_rate']}%")
        lines.append("")

        change = comp["change"]
        lines.append(f"  Change in Total Tasks: {change['total_tasks']:+d}")
        lines.append(f"  Change in Completed: {change['completed']:+d}")
        lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)


class JSONFormatter:
    """Format reports as JSON."""

    def format_report(self, report: Dict[str, Any]) -> str:
        """Format report as JSON string."""
        return json.dumps(report, indent=2, default=str)


class CSVFormatter:
    """Format task data as CSV."""

    def format_tasks(self, tasks: List[Dict[str, Any]]) -> str:
        """Format tasks as CSV string."""
        if not tasks:
            return ""

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=tasks[0].keys())
        writer.writeheader()
        writer.writerows(tasks)

        return output.getvalue()
