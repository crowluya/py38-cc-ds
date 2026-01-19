"""CSV report exporter."""

import csv
from typing import Optional
from io import StringIO

from .base import BaseExporter
from ..models import AnalysisResult


class CSVExporter(BaseExporter):
    """Export analysis results to CSV format."""

    def export(self, result: AnalysisResult, output_path: Optional[str] = None) -> str:
        """Export to CSV.

        Args:
            result: Analysis result
            output_path: Optional file path

        Returns:
            CSV string or file path if written
        """
        output = StringIO()

        # Create CSV writer
        writer = csv.writer(output)

        # Write summary section
        writer.writerow(["Log Analysis Report"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Source File", result.source_file])
        writer.writerow(["Total Entries", result.total_entries])
        writer.writerow(["Analyzed Entries", result.analyzed_entries])
        writer.writerow(["Analysis Duration (s)", f"{result.analysis_duration:.2f}"])
        writer.writerow(["Error Rate (%)", f"{result.error_rate * 100:.2f}"])

        if result.average_response_time:
            writer.writerow(["Average Response Time (ms)", f"{result.average_response_time:.2f}"])

        if result.total_response_size:
            writer.writerow(["Total Response Size", result.total_response_size])

        writer.writerow([])  # Empty row

        # Write log level counts
        writer.writerow(["Log Level Distribution"])
        writer.writerow(["Level", "Count"])
        for level, count in sorted(result.log_level_counts.items()):
            writer.writerow([level, count])

        writer.writerow([])  # Empty row

        # Write anomalies
        writer.writerow(["Anomalies Detected"])
        writer.writerow([
            "Type", "Severity", "Severity Level", "Description", "Confidence",
            "Occurrences", "First Seen", "Last Seen", "Pattern", "Metric"
        ])

        for anomaly in result.anomalies:
            writer.writerow([
                anomaly.anomaly_type,
                f"{anomaly.severity:.2f}",
                anomaly.severity_level.value,
                anomaly.description,
                f"{anomaly.confidence:.2%}",
                anomaly.occurrence_count,
                anomaly.first_seen.isoformat() if anomaly.first_seen else "",
                anomaly.last_seen.isoformat() if anomaly.last_seen else "",
                anomaly.pattern or "",
                anomaly.context.get("metric", ""),
            ])

        writer.writerow([])  # Empty row

        # Write insights
        writer.writerow(["Actionable Insights"])
        writer.writerow(["Category", "Title", "Priority", "Description", "Recommendation"])

        for insight in result.insights:
            writer.writerow([
                insight.category,
                insight.title,
                insight.priority,
                insight.description,
                insight.recommendation,
            ])

        csv_str = output.getvalue()
        output.close()

        # Write to file if path specified
        if output_path:
            with open(output_path, 'w') as f:
                f.write(csv_str)
            return output_path

        return csv_str
