"""Console output formatter with colors and formatting."""

from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from pylint_integrator.formatters.base import BaseFormatter
from pylint_integrator.core.results import AnalysisResult, MessageType


class ConsoleFormatter(BaseFormatter):
    """Formatter for console output with colors and rich formatting."""

    def __init__(self):
        """Initialize console formatter."""
        self.console = Console()

        # Color mapping
        self.type_colors = {
            MessageType.FATAL: "bold red",
            MessageType.ERROR: "red",
            MessageType.WARNING: "yellow",
            MessageType.CONVENTION: "blue",
            MessageType.REFACTOR: "cyan",
            MessageType.INFO: "dim",
        }

    def format(self, result: AnalysisResult) -> str:
        """
        Format complete analysis result for console output.

        Args:
            result: Analysis result to format

        Returns:
            Formatted console output
        """
        output = []

        # Header
        output.append(self._format_header(result))

        # Summary
        output.append(self._format_summary(result))

        # Score panel
        if result.global_score is not None:
            output.append(self._format_score(result))

        # Issues table
        if result.issues:
            output.append(self._format_issues_table(result))
        else:
            output.append(self._format_no_issues())

        # Module stats
        if result.module_stats:
            output.append(self._format_module_stats(result))

        # Metrics
        if result.metrics:
            output.append(self._format_metrics(result))

        # Build output string
        with self.console.capture() as capture:
            for section in output:
                self.console.print(section)
            return capture.get()

    def _format_header(self, result: AnalysisResult) -> Panel:
        """Format header section."""
        header_text = Text()
        header_text.append("Pylint Analysis Report", style="bold blue")
        header_text.append(f"\nPython {result.python_version}", style="dim")
        header_text.append(f"\n{result.pylint_version}", style="dim")

        return Panel(
            header_text,
            title="🔍 Pylint Integrator",
            border_style="blue",
        )

    def _format_summary(self, result: AnalysisResult) -> Panel:
        """Format summary section."""
        summary_text = Text()
        summary_text.append(f"Files Analyzed: {result.files_analyzed}\n", style="cyan")
        summary_text.append(f"Modules: {result.modules_analyzed}\n", style="cyan")
        summary_text.append(f"Execution Time: {result.execution_time:.2f}s\n", style="cyan")

        # Issue counts
        summary_text.append("\nIssue Breakdown:\n", style="bold")
        summary_text.append(f"  Fatal: {result.fatal_count}\n", style=self.type_colors[MessageType.FATAL])
        summary_text.append(f"  Errors: {result.error_count}\n", style=self.type_colors[MessageType.ERROR])
        summary_text.append(f"  Warnings: {result.warning_count}\n", style=self.type_colors[MessageType.WARNING])
        summary_text.append(f"  Conventions: {result.convention_count}\n", style=self.type_colors[MessageType.CONVENTION])
        summary_text.append(f"  Refactors: {result.refactor_count}\n", style=self.type_colors[MessageType.REFACTOR])
        summary_text.append(f"  Info: {result.info_count}", style=self.type_colors[MessageType.INFO])

        return Panel(summary_text, title="📊 Summary", border_style="cyan")

    def _format_score(self, result: AnalysisResult) -> Panel:
        """Format score panel."""
        score = result.global_score or 0

        # Determine color based on score
        if score >= 9:
            color = "green"
            emoji = "🌟"
        elif score >= 7:
            color = "yellow"
            emoji = "👍"
        elif score >= 5:
            color = "orange"
            emoji = "⚠️"
        else:
            color = "red"
            emoji = "❌"

        score_text = Text()
        score_text.append(f"{score:.2f}", style=f"bold {color}")
        score_text.append("/10.0", style="dim")

        return Panel(
            score_text,
            title=f"{emoji} Code Quality Score",
            border_style=color,
        )

    def _format_issues_table(self, result: AnalysisResult) -> Table:
        """Format issues as a table."""
        table = Table(
            title="🐛 Issues Found",
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED,
        )

        table.add_column("Location", style="cyan", no_wrap=False)
        table.add_column("Type", style="magenta", width=10)
        table.add_column("ID", style="yellow", width=8)
        table.add_column("Message", style="white")

        for issue in result.issues[:100]:  # Limit to first 100
            type_style = self.type_colors.get(issue.type, "white")
            table.add_row(
                issue.location_str,
                Text(str(issue.type), style=type_style),
                issue.msg_id,
                issue.message,
            )

        if result.total_issues > 100:
            table.add_row(
                "...",
                Text("", style="dim"),
                "",
                Text(f"... and {result.total_issues - 100} more", style="dim"),
            )

        return table

    def _format_no_issues(self) -> Panel:
        """Format message when no issues found."""
        return Panel(
            Text("✅ No issues found!", style="bold green"),
            border_style="green",
        )

    def _format_module_stats(self, result: AnalysisResult) -> Table:
        """Format module statistics."""
        table = Table(
            title="📦 Module Statistics",
            show_header=True,
            header_style="bold blue",
            box=box.ROUNDED,
        )

        table.add_column("Module", style="cyan")
        table.add_column("Path", style="dim")
        table.add_column("Issues", style="yellow")
        table.add_column("Score", style="green", justify="right")

        # Sort by issue count (descending)
        sorted_stats = sorted(result.module_stats, key=lambda m: m.total_issues, reverse=True)

        for stats in sorted_stats[:20]:  # Top 20 modules
            table.add_row(
                stats.module,
                stats.path,
                str(stats.total_issues),
                f"{stats.score:.2f}" if stats.score else "N/A",
            )

        return table

    def _format_metrics(self, result: AnalysisResult) -> Table:
        """Format metrics table."""
        table = Table(
            title="📈 Metrics",
            show_header=True,
            header_style="bold green",
            box=box.ROUNDED,
            show_lines=False,
        )

        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow", justify="right")
        table.add_column("Change", style="green", justify="right")

        for metric in result.metrics:
            change_str = ""
            if metric.change is not None:
                change = metric.change
                if change > 0:
                    change_str = Text(f"+{change:.1f}", style="red")
                elif change < 0:
                    change_str = Text(f"{change:.1f}", style="green")
                else:
                    change_str = Text("0.0", style="dim")

            table.add_row(
                metric.name,
                f"{metric.value:.1f}",
                change_str if change_str else Text("N/A", style="dim"),
            )

        return table

    def format_summary(self, result: AnalysisResult) -> str:
        """Format only summary."""
        with self.console.capture() as capture:
            self.console.print(self._format_summary(result))
            return capture.get()

    def format_issues(self, result: AnalysisResult) -> str:
        """Format only issues."""
        with self.console.capture() as capture:
            if result.issues:
                self.console.print(self._format_issues_table(result))
            return capture.get()

    def format_metrics(self, result: AnalysisResult) -> str:
        """Format only metrics."""
        with self.console.capture() as capture:
            if result.metrics:
                self.console.print(self._format_metrics(result))
            return capture.get()
