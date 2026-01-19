"""Statistical anomaly detection using Z-score, IQR, and other methods."""

import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

from ..models import LogEntry, Anomaly, SeverityLevel, LogLevel
from ..config import AnalysisConfig


class StatisticalDetector:
    """Statistical anomaly detector using various statistical methods."""

    def __init__(self, config: AnalysisConfig):
        """Initialize statistical detector.

        Args:
            config: Analysis configuration
        """
        self.config = config
        self.baseline_stats = {}

    def detect(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect statistical anomalies in log entries.

        Args:
            entries: List of log entries to analyze

        Returns:
            List of detected anomalies
        """
        if not entries:
            return []

        anomalies = []

        # Detect anomalies in response times
        if self._has_response_times(entries):
            response_time_anomalies = self._detect_response_time_anomalies(entries)
            anomalies.extend(response_time_anomalies)

        # Detect anomalies in response sizes
        if self._has_response_sizes(entries):
            size_anomalies = self._detect_response_size_anomalies(entries)
            anomalies.extend(size_anomalies)

        # Detect error rate spikes
        error_rate_anomalies = self._detect_error_rate_anomalies(entries)
        anomalies.extend(error_rate_anomalies)

        # Detect status code anomalies
        status_anomalies = self._detect_status_anomalies(entries)
        anomalies.extend(status_anomalies)

        # Detect request volume spikes
        volume_anomalies = self._detect_volume_anomalies(entries)
        anomalies.extend(volume_anomalies)

        return anomalies

    def _has_response_times(self, entries: List[LogEntry]) -> bool:
        """Check if entries have response time data."""
        return any(e.response_time is not None for e in entries)

    def _has_response_sizes(self, entries: List[LogEntry]) -> bool:
        """Check if entries have response size data."""
        return any(e.response_size is not None for e in entries)

    def _detect_response_time_anomalies(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect response time anomalies using Z-score and IQR."""
        # Extract response times
        response_times = [(i, e) for i, e in enumerate(entries) if e.response_time is not None]

        if len(response_times) < self.config.baseline_window // 10:
            return []

        times = [rt for _, rt in response_times]
        values = np.array([e.response_time for _, e in response_times])

        # Calculate statistics
        mean = np.mean(values)
        std = np.std(values)
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1

        anomalies = []

        # Z-score method
        zscore_threshold = self.config.zscore_threshold
        zscore_anomalies = [(i, e) for i, e in response_times
                           if abs((e.response_time - mean) / std) > zscore_threshold if std > 0]

        # IQR method
        iqr_threshold = q3 + (self.config.iqr_multiplier * iqr)
        iqr_anomalies = [(i, e) for i, e in response_times if e.response_time > iqr_threshold]

        # Combine and deduplicate
        anomaly_indices = set()
        for i, e in zscore_anomalies:
            anomaly_indices.add(i)
        for i, e in iqr_anomalies:
            anomaly_indices.add(i)

        if anomaly_indices:
            affected_entries = [entries[i] for i in anomaly_indices]

            # Calculate severity based on deviation
            max_deviation = max(abs(e.response_time - mean) / std if std > 0 else 0
                              for e in affected_entries)

            severity = min(10, max_deviation / 2)
            severity_level = self._get_severity_level(severity)

            anomaly = Anomaly(
                anomaly_type="statistical",
                severity=severity,
                severity_level=severity_level,
                description=f"Unusual response times detected (mean: {mean:.2f}ms, max: {max(e.response_time for e in affected_entries):.2f}ms)",
                confidence=min(1.0, len(affected_entries) / len(response_times)),
                affected_entries=affected_entries,
                first_seen=min(e.timestamp for e in affected_entries),
                last_seen=max(e.timestamp for e in affected_entries),
                occurrence_count=len(affected_entries),
                expected_value=mean,
                actual_value=np.mean([e.response_time for e in affected_entries]),
                deviation=max_deviation,
                z_score=max(abs((e.response_time - mean) / std) for e in affected_entries if std > 0),
                context={"metric": "response_time", "baseline_mean": mean, "baseline_std": std}
            )

            anomalies.append(anomaly)

        return anomalies

    def _detect_response_size_anomalies(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect response size anomalies."""
        # Extract response sizes
        response_sizes = [(i, e) for i, e in enumerate(entries) if e.response_size is not None]

        if len(response_sizes) < self.config.baseline_window // 10:
            return []

        values = np.array([e.response_size for _, e in response_sizes])

        # Calculate statistics
        mean = np.mean(values)
        std = np.std(values)
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1

        anomalies = []
        anomaly_indices = set()

        # Z-score method
        for i, e in response_sizes:
            if std > 0:
                z_score = abs((e.response_size - mean) / std)
                if z_score > self.config.zscore_threshold:
                    anomaly_indices.add(i)

        # IQR method
        iqr_threshold = q3 + (self.config.iqr_multiplier * iqr)
        for i, e in response_sizes:
            if e.response_size > iqr_threshold:
                anomaly_indices.add(i)

        if anomaly_indices:
            affected_entries = [entries[i] for i in anomaly_indices]

            max_deviation = max(abs(e.response_size - mean) / std if std > 0 else 0
                              for e in affected_entries)

            severity = min(10, max_deviation / 2)
            severity_level = self._get_severity_level(severity)

            anomaly = Anomaly(
                anomaly_type="statistical",
                severity=severity,
                severity_level=severity_level,
                description=f"Unusual response sizes detected (mean: {mean:.0f} bytes, max: {max(e.response_size for e in affected_entries):.0f} bytes)",
                confidence=min(1.0, len(affected_entries) / len(response_sizes)),
                affected_entries=affected_entries,
                first_seen=min(e.timestamp for e in affected_entries),
                last_seen=max(e.timestamp for e in affected_entries),
                occurrence_count=len(affected_entries),
                expected_value=mean,
                actual_value=np.mean([e.response_size for e in affected_entries]),
                deviation=max_deviation,
                context={"metric": "response_size", "baseline_mean": mean, "baseline_std": std}
            )

            anomalies.append(anomaly)

        return anomalies

    def _detect_error_rate_anomalies(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect error rate spikes using moving window analysis."""
        if len(entries) < self.config.moving_average_window * 2:
            return []

        # Calculate error rate in sliding window
        window_size = self.config.moving_average_window
        error_rates = []

        for i in range(window_size, len(entries)):
            window = entries[i - window_size:i]
            error_count = sum(1 for e in window if e.level in [LogLevel.ERROR, LogLevel.CRITICAL])
            error_rate = error_count / window_size
            error_rates.append((i, error_rate))

        if not error_rates:
            return []

        # Calculate baseline
        rates = [r for _, r in error_rates]
        mean_rate = np.mean(rates)
        std_rate = np.std(rates)

        anomalies = []

        if std_rate > 0:
            # Detect spikes
            spike_threshold = mean_rate + (self.config.zscore_threshold * std_rate)

            for i, rate in error_rates:
                if rate > spike_threshold and rate > self.config.min_error_rate:
                    window_entries = entries[max(0, i - window_size):i]
                    error_entries = [e for e in window_entries
                                   if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]]

                    if error_entries:
                        severity = min(10, (rate / mean_rate) * 5) if mean_rate > 0 else 8
                        severity_level = self._get_severity_level(severity)

                        anomaly = Anomaly(
                            anomaly_type="spike",
                            severity=severity,
                            severity_level=severity_level,
                            description=f"Error rate spike detected ({rate * 100:.1f}% vs baseline {mean_rate * 100:.1f}%)",
                            confidence=min(1.0, rate / spike_threshold),
                            affected_entries=error_entries,
                            first_seen=min(e.timestamp for e in error_entries),
                            last_seen=max(e.timestamp for e in error_entries),
                            occurrence_count=len(error_entries),
                            expected_value=mean_rate,
                            actual_value=rate,
                            deviation=rate - mean_rate,
                            context={"metric": "error_rate", "window_size": window_size}
                        )

                        anomalies.append(anomaly)

        return anomalies

    def _detect_status_anomalies(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect unusual status code patterns."""
        # Group by status code
        status_counts = defaultdict(list)
        for i, e in enumerate(entries):
            if e.status_code:
                status_counts[e.status_code].append(i)

        anomalies = []

        # Check for 5xx errors
        if 500 in status_counts or 502 in status_counts or 503 in status_counts:
            server_error_indices = []
            for code in [500, 502, 503]:
                server_error_indices.extend(status_counts.get(code, []))

            if server_error_indices:
                affected_entries = [entries[i] for i in server_error_indices]
                severity = 9 if 503 in status_counts else 8

                anomaly = Anomaly(
                    anomaly_type="pattern",
                    severity=severity,
                    severity_level=SeverityLevel.CRITICAL,
                    description=f"Server errors detected ({len(server_error_indices)} occurrences)",
                    confidence=0.9,
                    affected_entries=affected_entries[:50],  # Limit sample
                    first_seen=min(e.timestamp for e in affected_entries),
                    last_seen=max(e.timestamp for e in affected_entries),
                    occurrence_count=len(server_error_indices),
                    pattern="5xx status codes",
                    pattern_frequency=len(server_error_indices),
                    context={"status_codes": {code: len(status_counts.get(code, []))
                                            for code in [500, 502, 503]}}
                )

                anomalies.append(anomaly)

        return anomalies

    def _detect_volume_anomalies(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect request volume anomalies."""
        if len(entries) < self.config.baseline_window:
            return []

        # Group entries by time buckets (1 minute)
        time_buckets = defaultdict(list)
        for entry in entries:
            # Round to nearest minute
            minute_key = entry.timestamp.replace(second=0, microsecond=0)
            time_buckets[minute_key].append(entry)

        if len(time_buckets) < 5:
            return []

        # Calculate requests per minute
        rpm_values = [len(entries) for entries in time_buckets.values()]
        mean_rpm = np.mean(rpm_values)
        std_rpm = np.std(rpm_values)

        anomalies = []

        if std_rpm > 0:
            # Detect volume spikes
            spike_threshold = mean_rpm + (self.config.zscore_threshold * std_rpm)

            for minute, bucket_entries in time_buckets.items():
                if len(bucket_entries) > spike_threshold:
                    severity = min(10, (len(bucket_entries) / mean_rpm) * 3) if mean_rpm > 0 else 7
                    severity_level = self._get_severity_level(severity)

                    anomaly = Anomaly(
                        anomaly_type="spike",
                        severity=severity,
                        severity_level=severity_level,
                        description=f"Request volume spike detected ({len(bucket_entries)} requests vs baseline {mean_rpm:.0f})",
                        confidence=0.8,
                        affected_entries=bucket_entries[:100],  # Limit sample
                        first_seen=minute,
                        last_seen=minute + timedelta(seconds=59),
                        occurrence_count=len(bucket_entries),
                        expected_value=mean_rpm,
                        actual_value=len(bucket_entries),
                        deviation=len(bucket_entries) - mean_rpm,
                        context={"metric": "request_volume", "requests_per_minute": len(bucket_entries)}
                    )

                    anomalies.append(anomaly)

        return anomalies

    def _get_severity_level(self, score: float) -> SeverityLevel:
        """Convert severity score to SeverityLevel."""
        if score >= 9:
            return SeverityLevel.CRITICAL
        elif score >= 7:
            return SeverityLevel.HIGH
        elif score >= 5:
            return SeverityLevel.MEDIUM
        elif score >= 3:
            return SeverityLevel.LOW
        else:
            return SeverityLevel.INFO
