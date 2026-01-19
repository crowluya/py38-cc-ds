"""HTML report exporter."""

from typing import Optional
from datetime import timedelta

from .base import BaseExporter
from ..models import AnalysisResult, SeverityLevel


class HTMLExporter(BaseExporter):
    """Export analysis results to HTML format."""

    # HTML template
    TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log Analysis Report - {source_file}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}

        h2 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 1.5em;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }}

        .summary-card h3 {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 5px;
            text-transform: uppercase;
        }}

        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}

        .severity-critical {{ border-left-color: #e74c3c; }}
        .severity-high {{ border-left-color: #e67e22; }}
        .severity-medium {{ border-left-color: #f39c12; }}
        .severity-low {{ border-left-color: #3498db; }}

        .anomaly-list {{
            margin-top: 20px;
        }}

        .anomaly {{
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 15px;
            transition: box-shadow 0.2s;
        }}

        .anomaly:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}

        .anomaly-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .anomaly-type {{
            font-size: 0.85em;
            color: #7f8c8d;
            text-transform: uppercase;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .badge-critical {{ background: #e74c3c; color: white; }}
        .badge-high {{ background: #e67e22; color: white; }}
        .badge-medium {{ background: #f39c12; color: white; }}
        .badge-low {{ background: #3498db; color: white; }}
        .badge-info {{ background: #95a5a6; color: white; }}

        .anomaly-description {{
            font-size: 1.1em;
            color: #2c3e50;
            margin-bottom: 10px;
        }}

        .anomaly-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            font-size: 0.9em;
            color: #7f8c8d;
        }}

        .insight {{
            background: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 6px;
        }}

        .insight-title {{
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
        }}

        .insight-recommendation {{
            color: #34495e;
            margin-top: 10px;
            padding: 10px;
            background: white;
            border-radius: 4px;
        }}

        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}

        .stats-table th,
        .stats-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}

        .stats-table th {{
            background: #f8f9fa;
            font-weight: 600;
        }}

        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}

        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #ecf0f1;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3498db, #2ecc71);
            transition: width 0.3s;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Log Analysis Report</h1>

        <!-- Summary Section -->
        <h2>Summary</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Source File</h3>
                <div class="value" style="font-size: 1.2em;">{source_file}</div>
            </div>
            <div class="summary-card">
                <h3>Total Entries</h3>
                <div class="value">{total_entries:,}</div>
            </div>
            <div class="summary-card">
                <h3>Anomalies Found</h3>
                <div class="value">{anomaly_count}</div>
            </div>
            <div class="summary-card severity-critical">
                <h3>Critical</h3>
                <div class="value">{critical_count}</div>
            </div>
            <div class="summary-card severity-high">
                <h3>High Severity</h3>
                <div class="value">{high_severity_count}</div>
            </div>
            <div class="summary-card">
                <h3>Analysis Time</h3>
                <div class="value">{analysis_time:.2f}s</div>
            </div>
        </div>

        <!-- Statistics Section -->
        <h2>Statistics</h2>
        <table class="stats-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Error Rate</td>
                <td>{error_rate:.2f}%</td>
            </tr>
            {response_time_row}
            {response_size_row}
        </table>

        <h3>Log Level Distribution</h3>
        {level_distribution}

        <!-- Anomalies Section -->
        <h2>Detected Anomalies</h2>
        <div class="anomaly-list">
            {anomalies_html}
        </div>

        <!-- Insights Section -->
        {insights_html}

        <!-- Footer -->
        <div class="footer">
            <p>Generated by LogAnalyzer at {generated_time}</p>
        </div>
    </div>
</body>
</html>
"""

    def export(self, result: AnalysisResult, output_path: Optional[str] = None) -> str:
        """Export to HTML.

        Args:
            result: Analysis result
            output_path: Optional file path

        Returns:
            HTML string or file path if written
        """
        # Build level distribution
        level_dist = self._build_level_distribution(result)

        # Build anomalies HTML
        anomalies_html = self._build_anomalies_html(result)

        # Build insights HTML
        insights_html = self._build_insights_html(result)

        # Build response time row
        response_time_row = ""
        if result.average_response_time:
            response_time_row = f"<tr><td>Average Response Time</td><td>{result.average_response_time:.2f}ms</td></tr>"

        # Build response size row
        response_size_row = ""
        if result.total_response_size:
            response_size_row = f"<tr><td>Total Response Size</td><td>{result.total_response_size:,} bytes</td></tr>"

        # Fill template
        html = self.TEMPLATE.format(
            source_file=result.source_file,
            total_entries=result.total_entries,
            anomaly_count=result.anomaly_count,
            critical_count=len(result.critical_anomalies),
            high_severity_count=len(result.high_severity_anomalies),
            analysis_time=result.analysis_duration,
            error_rate=result.error_rate * 100,
            response_time_row=response_time_row,
            response_size_row=response_size_row,
            level_distribution=level_dist,
            anomalies_html=anomalies_html,
            insights_html=insights_html,
            generated_time=result.end_time.strftime('%Y-%m-%d %H:%M:%S')
        )

        # Write to file if path specified
        if output_path:
            with open(output_path, 'w') as f:
                f.write(html)
            return output_path

        return html

    def _build_level_distribution(self, result: AnalysisResult) -> str:
        """Build log level distribution HTML."""
        if not result.log_level_counts:
            return "<p>No log level data available</p>"

        total = sum(result.log_level_counts.values())

        rows = []
        for level, count in sorted(result.log_level_counts.items()):
            percentage = (count / total * 100) if total > 0 else 0
            rows.append(f"""
                <tr>
                    <td>{level}</td>
                    <td>{count:,}</td>
                    <td>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {percentage:.1f}%"></div>
                        </div>
                    </td>
                    <td>{percentage:.1f}%</td>
                </tr>
            """)

        return f'<table class="stats-table"><tr><th>Level</th><th>Count</th><th colspan="2">Distribution</th></tr>{"".join(rows)}</table>'

    def _build_anomalies_html(self, result: AnalysisResult) -> str:
        """Build anomalies HTML."""
        if not result.anomalies:
            return "<p>No anomalies detected</p>"

        items = []
        for anomaly in result.anomalies[:50]:  # Limit to 50
            badge_class = f"badge-{anomaly.severity_level.value.lower()}"

            # Build details
            details = [
                f"<div><strong>Severity:</strong> {anomaly.severity:.1f}/10</div>",
                f"<div><strong>Confidence:</strong> {anomaly.confidence:.1%}</div>",
                f"<div><strong>Occurrences:</strong> {anomaly.occurrence_count:,}</div>",
            ]

            if anomaly.duration:
                duration_str = str(timedelta(seconds=int(anomaly.duration)))
                details.append(f"<div><strong>Duration:</strong> {duration_str}</div>")

            if anomaly.context.get("metric"):
                details.append(f"<div><strong>Metric:</strong> {anomaly.context['metric']}</div>")

            items.append(f"""
                <div class="anomaly">
                    <div class="anomaly-header">
                        <span class="anomaly-type">{anomaly.anomaly_type}</span>
                        <span class="badge {badge_class}">{anomaly.severity_level.value}</span>
                    </div>
                    <div class="anomaly-description">{anomaly.description}</div>
                    <div class="anomaly-details">
                        {"".join(details)}
                    </div>
                </div>
            """)

        return "".join(items)

    def _build_insights_html(self, result: AnalysisResult) -> str:
        """Build insights HTML."""
        if not result.insights:
            return ""

        items = []
        for insight in result.insights:
            items.append(f"""
                <div class="insight">
                    <div class="insight-title">📊 [{insight.category.upper()}] {insight.title}</div>
                    <div><strong>Priority:</strong> {insight.priority.upper()}</div>
                    <div>{insight.description}</div>
                    <div class="insight-recommendation">
                        <strong>💡 Recommendation:</strong> {insight.recommendation}
                    </div>
                </div>
            """)

        return f'<h2>Actionable Insights</h2>{"".join(items)}'
