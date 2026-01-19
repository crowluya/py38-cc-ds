"""JSON report exporter."""

import json
from typing import Optional

from .base import BaseExporter
from ..models import AnalysisResult


class JSONExporter(BaseExporter):
    """Export analysis results to JSON format."""

    def export(self, result: AnalysisResult, output_path: Optional[str] = None) -> str:
        """Export to JSON.

        Args:
            result: Analysis result
            output_path: Optional file path

        Returns:
            JSON string or file path if written
        """
        data = result.to_dict()

        # Apply configuration
        if self.config and hasattr(self.config, 'json'):
            json_config = self.config.json
            if not json_config.include_raw:
                # Remove raw log lines from sample entries
                for anomaly in data.get('anomalies', {}).get('details', []):
                    for entry in anomaly.get('sample_entries', []):
                        entry.pop('raw_line', None)

        # Convert to JSON
        json_str = json.dumps(
            data,
            indent=2 if (not self.config or not hasattr(self.config, 'json') or
                        self.config.json.pretty) else None,
            default=str  # Handle datetime and other non-serializable objects
        )

        # Write to file if path specified
        if output_path:
            with open(output_path, 'w') as f:
                f.write(json_str)
            return output_path

        return json_str
