"""Text-based visualization charts for terminal output."""

from typing import Dict, List, Any, Optional


class TextCharts:
    """
    Create text-based charts for terminal display.

    Provides ASCII art charts for displaying data in
    terminal environments.
    """

    @staticmethod
    def bar_chart(
        data: Dict[str, int],
        width: int = 50,
        title: Optional[str] = None,
    ) -> str:
        """
        Create horizontal bar chart.

        Args:
            data: Dictionary with labels as keys, values as values
            width: Maximum width of bars
            title: Optional chart title

        Returns:
            String containing the chart
        """
        if not data:
            return "No data available"

        lines = []
        if title:
            lines.append(title)
            lines.append("=" * len(title))

        max_value = max(data.values()) if data.values() else 1
        max_label_len = max(len(str(k)) for k in data.keys())

        for label, value in data.items():
            bar_length = int((value / max_value) * width)
            bar = "█" * bar_length
            lines.append(f"{str(label).ljust(max_label_len)} │ {bar} {value}")

        return "\n".join(lines)

    @staticmethod
    def line_chart(
        data: List[Dict[str, Any]],
        x_key: str,
        y_key: str,
        height: int = 10,
        width: int = 50,
    ) -> str:
        """
        Create simple line chart.

        Args:
            data: List of dictionaries with x and y values
            x_key: Key for x-axis values
            y_key: Key for y-axis values
            height: Chart height
            width: Chart width

        Returns:
            String containing the chart
        """
        if not data:
            return "No data available"

        # Extract values
        x_values = [str(d[x_key]) for d in data]
        y_values = [d[y_key] for d in data]

        if not y_values:
            return "No data available"

        max_y = max(y_values) if y_values else 1
        min_y = min(y_values) if y_values else 0

        # Create chart
        lines = []
        lines.append(" " * 15 + "─" * width)

        for i in range(height, 0, -1):
            y_value = min_y + (max_y - min_y) * (i / height)
            line = f"{y_value:10.1f} │"

            for y in y_values:
                if y >= y_value:
                    line += " ●"
                else:
                    line += "  "
            lines.append(line)

        lines.append(" " * 15 + "─" * width)

        # X-axis labels (show first and last)
        if len(x_values) > 1:
            x_label = f"{x_values[0]}{' ' * (width - len(x_values[0]) - len(x_values[-1]))}{x_values[-1]}"
            lines.append(" " * 12 + x_label)

        return "\n".join(lines)

    @staticmethod
    def pie_chart(data: Dict[str, int]) -> str:
        """
        Create simple text pie chart.

        Args:
            data: Dictionary with labels as keys, values as values

        Returns:
            String containing the chart
        """
        if not data:
            return "No data available"

        total = sum(data.values())
        if total == 0:
            return "No data available"

        lines = []
        lines.append("Distribution:")
        lines.append("-" * 40)

        for label, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
            percentage = (value / total) * 100
            bar_length = int(percentage / 2)
            bar = "█" * bar_length
            lines.append(f"{label:20} │ {bar} {percentage:.1f}% ({value})")

        return "\n".join(lines)

    @staticmethod
    def sparkline(data: List[int], width: int = 40) -> str:
        """
        Create sparkline (mini line chart).

        Args:
            data: List of numeric values
            width: Maximum width of sparkline

        Returns:
            String containing the sparkline
        """
        if not data:
            return "█" * width

        # Resample data to fit width
        if len(data) > width:
            step = len(data) / width
            resampled = [data[int(i * step)] for i in range(width)]
        else:
            resampled = data

        min_val = min(resampled)
        max_val = max(resampled)

        if max_val == min_val:
            return "─" * len(resampled)

        # Create sparkline characters
        chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        sparkline = ""

        for val in resampled:
            normalized = (val - min_val) / (max_val - min_val)
            char_idx = int(normalized * (len(chars) - 1))
            sparkline += chars[char_idx]

        return sparkline

    @staticmethod
    def progress_bar(
        current: int,
        total: int,
        width: int = 40,
        label: Optional[str] = None,
    ) -> str:
        """
        Create progress bar.

        Args:
            current: Current value
            total: Total value
            width: Bar width
            label: Optional label

        Returns:
            String containing the progress bar
        """
        if total == 0:
            percentage = 0
        else:
            percentage = (current / total) * 100

        filled = int((current / total) * width) if total > 0 else 0
        bar = "█" * filled + "░" * (width - filled)

        if label:
            return f"{label}: [{bar}] {percentage:.1f}% ({current}/{total})"
        return f"[{bar}] {percentage:.1f}% ({current}/{total})"


class ChartGenerator:
    """
    Generate various visualization charts.

    Higher-level interface for creating charts from
    task performance data.
    """

    def __init__(self):
        """Initialize chart generator."""
        self.text_charts = TextCharts()

    def generate_completion_chart(
        self, metrics: Dict[str, Any]
    ) -> str:
        """
        Generate completion status chart.

        Args:
            metrics: Metrics dictionary

        Returns:
            Formatted chart string
        """
        by_status = metrics.get("by_status", {})

        return self.text_charts.pie_chart(by_status)

    def generate_productivity_chart(
        self, productivity_data: Dict[str, Any]
    ) -> str:
        """
        Generate productivity trend chart.

        Args:
            productivity_data: Productivity data dictionary

        Returns:
            Formatted chart string
        """
        daily = productivity_data.get("daily_breakdown", [])

        if not daily:
            return "No productivity data available"

        # Create chart from daily breakdown
        chart_data = [
            {"date": d["date"][-5:], "created": d["created"]}
            for d in daily[-14:]  # Last 14 days
        ]

        return self.text_charts.line_chart(
            chart_data,
            x_key="date",
            y_key="created",
            height=8,
            width=40,
        )

    def generate_priority_distribution(
        self, metrics: Dict[str, Any]
    ) -> str:
        """
        Generate priority distribution chart.

        Args:
            metrics: Metrics dictionary

        Returns:
            Formatted chart string
        """
        by_priority = metrics.get("by_priority", {})

        return self.text_charts.bar_chart(
            by_priority,
            width=30,
            title="Priority Distribution",
        )

    def generate_velocity_chart(
        self, velocity_data: Dict[str, Any]
    ) -> str:
        """
        Generate velocity sparkline.

        Args:
            velocity_data: Velocity trend data

        Returns:
            Formatted chart string
        """
        daily_velocity = velocity_data.get("daily_velocity", {})

        if not daily_velocity:
            return "No velocity data available"

        values = list(daily_velocity.values())

        return f"Velocity: {self.text_charts.sparkline(values, width=30)}"

    def generate_bottleneck_summary(
        self, bottlenecks: List[Dict[str, Any]]
    ) -> str:
        """
        Generate bottleneck summary visualization.

        Args:
            bottlenecks: List of bottleneck items

        Returns:
            Formatted summary string
        """
        if not bottlenecks:
            return "No bottlenecks detected"

        lines = []
        lines.append("⚠️  BOTTLENECKS DETECTED")
        lines.append("=" * 50)

        for i, b in enumerate(bottlenecks[:5], 1):
            b_type = b["type"].upper()
            title = b["title"][:40]

            if b_type == "LONG_RUNNING":
                lines.append(f"{i}. {title}")
                lines.append(f"   Type: Long running ({b['hours_in_progress']:.1f} hours)")
            elif b_type == "OVERDUE":
                lines.append(f"{i}. {title}")
                lines.append(f"   Type: Overdue by {b['overdue_by']} min")
            else:
                lines.append(f"{i}. {title}")
                lines.append(f"   Type: {b_type}")

            lines.append("")

        return "\n".join(lines)

    def generate_efficiency_gauge(
        self, efficiency_score: float
    ) -> str:
        """
        Generate efficiency gauge visualization.

        Args:
            efficiency_score: Efficiency score (0-100)

        Returns:
            Formatted gauge string
        """
        # Determine color indicator
        if efficiency_score >= 70:
            emoji = "🟢"
            status = "Excellent"
        elif efficiency_score >= 50:
            emoji = "🟡"
            status = "Good"
        else:
            emoji = "🔴"
            status = "Needs Improvement"

        return f"{emoji} Efficiency: {efficiency_score:.1f}% ({status})"
