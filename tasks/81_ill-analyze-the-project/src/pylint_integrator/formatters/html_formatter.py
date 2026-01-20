"""HTML output formatter."""

from jinja2 import Template

from pylint_integrator.formatters.base import BaseFormatter
from pylint_integrator.core.results import AnalysisResult, MessageType


class HTMLFormatter(BaseFormatter):
    """Formatter for HTML output."""

    # HTML template for the report
    TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pylint Analysis Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .header .meta {
            opacity: 0.9;
            font-size: 0.9rem;
        }

        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f9f9f9;
        }

        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }

        .summary-card .label {
            font-size: 0.85rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }

        .summary-card .value {
            font-size: 2rem;
            font-weight: bold;
            color: #333;
        }

        .summary-card.score .value {
            font-size: 3rem;
        }

        .score-excellent { color: #28a745; }
        .score-good { color: #ffc107; }
        .score-fair { color: #fd7e14; }
        .score-poor { color: #dc3545; }

        .section {
            padding: 30px;
            border-bottom: 1px solid #e9ecef;
        }

        .section-title {
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }

        .issues-table {
            width: 100%;
            border-collapse: collapse;
        }

        .issues-table th,
        .issues-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }

        .issues-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }

        .issues-table tr:hover {
            background: #f8f9fa;
        }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge-fatal { background: #dc3545; color: white; }
        .badge-error { background: #e74c3c; color: white; }
        .badge-warning { background: #ffc107; color: #333; }
        .badge-convention { background: #17a2b8; color: white; }
        .badge-refactor { background: #6f42c1; color: white; }
        .badge-info { background: #6c757d; color: white; }

        .location {
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            color: #666;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }

        .metric-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }

        .metric-card .name {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 5px;
        }

        .metric-card .value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #333;
        }

        .metric-card .change {
            font-size: 0.85rem;
            margin-top: 5px;
        }

        .change-positive { color: #dc3545; }
        .change-negative { color: #28a745; }
        .change-neutral { color: #6c757d; }

        .module-stats-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }

        .module-stats-table th,
        .module-stats-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }

        .footer {
            padding: 20px;
            text-align: center;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Pylint Analysis Report</h1>
            <div class="meta">
                Generated: {{ result.timestamp.isoformat() }} |
                Python {{ result.python_version }} |
                {{ result.pylint_version }}
            </div>
        </div>

        <div class="summary">
            <div class="summary-card score">
                <div class="label">Code Quality Score</div>
                <div class="value {% if result.global_score >= 9 %}score-excellent{% elif result.global_score >= 7 %}score-good{% elif result.global_score >= 5 %}score-fair{% else %}score-poor{% endif %}">
                    {{ "%.2f"|format(result.global_score or 0) }}
                </div>
            </div>

            <div class="summary-card">
                <div class="label">Total Issues</div>
                <div class="value">{{ result.total_issues }}</div>
            </div>

            <div class="summary-card">
                <div class="label">Modules Analyzed</div>
                <div class="value">{{ result.modules_analyzed }}</div>
            </div>

            <div class="summary-card">
                <div class="label">Execution Time</div>
                <div class="value">{{ "%.2f"|format(result.execution_time) }}s</div>
            </div>
        </div>

        {% if result.issues %}
        <div class="section">
            <h2 class="section-title">🐛 Issues ({{ result.total_issues }})</h2>
            <table class="issues-table">
                <thead>
                    <tr>
                        <th>Location</th>
                        <th>Type</th>
                        <th>ID</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
                    {% for issue in result.issues[:200] %}
                    <tr>
                        <td class="location">{{ issue.location_str }}</td>
                        <td>
                            <span class="badge badge-{{ issue.severity }}">
                                {{ issue.type }}
                            </span>
                        </td>
                        <td>{{ issue.msg_id }}</td>
                        <td>{{ issue.message }}</td>
                    </tr>
                    {% endfor %}
                    {% if result.total_issues > 200 %}
                    <tr>
                        <td colspan="4" style="text-align: center; color: #666;">
                            ... and {{ result.total_issues - 200 }} more issues
                        </td>
                    </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if result.module_stats %}
        <div class="section">
            <h2 class="section-title">📦 Module Statistics</h2>
            <table class="module-stats-table">
                <thead>
                    <tr>
                        <th>Module</th>
                        <th>Fatal</th>
                        <th>Error</th>
                        <th>Warning</th>
                        <th>Convention</th>
                        <th>Refactor</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    {% for stat in result.module_stats|sort(attribute='total_issues', reverse=true)[:20] %}
                    <tr>
                        <td>{{ stat.module }}</td>
                        <td>{{ stat.fatal }}</td>
                        <td>{{ stat.error }}</td>
                        <td>{{ stat.warning }}</td>
                        <td>{{ stat.convention }}</td>
                        <td>{{ stat.refactor }}</td>
                        <td><strong>{{ stat.total_issues }}</strong></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if result.metrics %}
        <div class="section">
            <h2 class="section-title">📈 Metrics</h2>
            <div class="metrics-grid">
                {% for metric in result.metrics %}
                <div class="metric-card">
                    <div class="name">{{ metric.name }}</div>
                    <div class="value">{{ "%.1f"|format(metric.value) }}</div>
                    {% if metric.change is not none %}
                    <div class="change {% if metric.change > 0 %}change-positive{% elif metric.change < 0 %}change-negative{% else %}change-neutral{% endif %}">
                        {% if metric.change > 0 %}+{% endif %}{{ "%.1f"|format(metric.change) }}
                        {% if metric.percentage_change is not none %}({{ "%.1f"|format(metric.percentage_change) }}%){% endif %}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="footer">
            Generated by Pylint Integrator v0.1.0
        </div>
    </div>
</body>
</html>
    """)  # noqa: E501

    def format(self, result: AnalysisResult) -> str:
        """
        Format complete analysis result as HTML.

        Args:
            result: Analysis result to format

        Returns:
            HTML string
        """
        return self.TEMPLATE.render(result=result)

    def format_summary(self, result: AnalysisResult) -> str:
        """Format summary as HTML."""
        return self.format(result)  # Full HTML includes summary

    def format_issues(self, result: AnalysisResult) -> str:
        """Format issues as HTML."""
        return self.format(result)  # Full HTML includes issues

    def format_metrics(self, result: AnalysisResult) -> str:
        """Format metrics as HTML."""
        return self.format(result)  # Full HTML includes metrics
