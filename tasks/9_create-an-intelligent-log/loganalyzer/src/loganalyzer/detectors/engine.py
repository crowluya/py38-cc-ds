"""Main anomaly detection engine that coordinates all detectors."""

from typing import List
from datetime import datetime

from ..models import LogEntry, Anomaly, AnalysisResult
from ..config import Config
from .statistical import StatisticalDetector
from .pattern import PatternDetector


class AnomalyDetector:
    """Main anomaly detection engine."""

    def __init__(self, config: Config):
        """Initialize detector with configuration.

        Args:
            config: Full configuration
        """
        self.config = config
        self.statistical_detector = StatisticalDetector(config.analysis)
        self.pattern_detector = PatternDetector(config.analysis)

    def analyze(self, entries: List[LogEntry], source_file: str = "") -> AnalysisResult:
        """Perform complete anomaly analysis on log entries.

        Args:
            entries: List of log entries to analyze
            source_file: Source file path for reference

        Returns:
            AnalysisResult with all anomalies and insights
        """
        start_time = datetime.now()

        if not entries:
            return AnalysisResult(
                source_file=source_file,
                total_entries=0,
                analyzed_entries=0,
                start_time=start_time,
                end_time=start_time,
            )

        # Calculate basic statistics
        stats = self._calculate_statistics(entries)

        # Run all detectors
        all_anomalies = []

        # Statistical detection
        statistical_anomalies = self.statistical_detector.detect(entries)
        all_anomalies.extend(statistical_anomalies)

        # Pattern detection
        pattern_anomalies = self.pattern_detector.detect(entries)
        all_anomalies.extend(pattern_anomalies)

        # Deduplicate and merge similar anomalies
        unique_anomalies = self._deduplicate_anomalies(all_anomalies)

        # Apply severity scoring
        scored_anomalies = self._apply_severity_scoring(unique_anomalies)

        # Generate insights
        insights = self._generate_insights(scored_anomalies, entries)

        # Sort anomalies by severity
        scored_anomalies.sort(key=lambda a: a.severity, reverse=True)

        end_time = datetime.now()

        # Create analysis result
        result = AnalysisResult(
            source_file=source_file,
            total_entries=len(entries),
            analyzed_entries=len(entries),
            start_time=start_time,
            end_time=end_time,
            log_level_counts=stats["level_counts"],
            error_rate=stats["error_rate"],
            average_response_time=stats["avg_response_time"],
            total_response_size=stats["total_response_size"],
            anomalies=scored_anomalies,
            insights=insights,
            analysis_duration=(end_time - start_time).total_seconds(),
        )

        return result

    def _calculate_statistics(self, entries: List[LogEntry]) -> dict:
        """Calculate basic statistics from log entries."""
        from collections import Counter
        from ..models import LogLevel

        # Log level counts
        level_counts = Counter(e.level.name for e in entries)

        # Error rate
        total = len(entries)
        errors = sum(1 for e in entries if e.level in [LogLevel.ERROR, LogLevel.CRITICAL])
        error_rate = errors / total if total > 0 else 0

        # Response time statistics
        response_times = [e.response_time for e in entries if e.response_time is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None

        # Response size
        response_sizes = [e.response_size for e in entries if e.response_size is not None]
        total_response_size = sum(response_sizes) if response_sizes else None

        return {
            "level_counts": dict(level_counts),
            "error_rate": error_rate,
            "avg_response_time": avg_response_time,
            "total_response_size": total_response_size,
        }

    def _deduplicate_anomalies(self, anomalies: List[Anomaly]) -> List[Anomaly]:
        """Remove duplicate anomalies and merge similar ones."""
        # Simple deduplication based on type and description
        seen = set()
        unique = []

        for anomaly in anomalies:
            # Create a key based on type and normalized description
            key = (anomaly.anomaly_type, anomaly.description[:100])

            if key not in seen:
                seen.add(key)
                unique.append(anomaly)
            else:
                # Merge with existing anomaly
                existing = next(a for a in unique if (a.anomaly_type, a.description[:100]) == key)
                # Combine affected entries (limited)
                existing.affected_entries = list(set(existing.affected_entries + anomaly.affected_entries))[:100]
                existing.occurrence_count += anomaly.occurrence_count
                # Update time range
                existing.first_seen = min(existing.first_seen, anomaly.first_seen)
                existing.last_seen = max(existing.last_seen, anomaly.last_seen)

        return unique

    def _apply_severity_scoring(self, anomalies: List[Anomaly]) -> List[Anomaly]:
        """Apply severity scoring based on configuration."""
        severity_config = self.config.severity

        for anomaly in anomalies:
            # Calculate weighted score
            weights = severity_config.weights

            # Frequency component
            freq_score = min(10, anomaly.occurrence_count / 10)

            # Deviation component
            dev_score = min(10, (anomaly.deviation or 0) * 2)

            # Impact component (based on type)
            impact_scores = {
                "statistical": 6,
                "pattern": 7,
                "spike": 8,
                "sequence": 7,
            }
            impact_score = impact_scores.get(anomaly.anomaly_type, 5)

            # Calculate weighted score
            final_score = (
                (weights.frequency * freq_score) +
                (weights.deviation * dev_score) +
                (weights.impact * impact_score)
            )

            # Adjust based on confidence
            final_score = final_score * anomaly.confidence

            # Update anomaly severity
            anomaly.severity = min(10, final_score)

            # Update severity level
            if anomaly.severity >= severity_config.critical_threshold:
                anomaly.severity_level = SeverityLevel.CRITICAL
            elif anomaly.severity >= severity_config.high_threshold:
                anomaly.severity_level = SeverityLevel.HIGH
            elif anomaly.severity >= severity_config.medium_threshold:
                anomaly.severity_level = SeverityLevel.MEDIUM
            elif anomaly.severity >= severity_config.low_threshold:
                anomaly.severity_level = SeverityLevel.LOW
            else:
                anomaly.severity_level = SeverityLevel.INFO

        return anomalies

    def _generate_insights(self, anomalies: List[Anomaly], entries: List[LogEntry]) -> List:
        """Generate actionable insights from anomalies."""
        from ..models import Insight

        insights = []

        # Performance insights
        performance_anomalies = [a for a in anomalies if "response_time" in a.context.get("metric", "")]
        if performance_anomalies:
            avg_deviation = sum(a.deviation or 0 for a in performance_anomalies) / len(performance_anomalies)

            insight = Insight(
                category="performance",
                title="Performance Degradation Detected",
                description=f"Response times are abnormally high. Average deviation: {avg_deviation:.1f}x from baseline.",
                recommendation="Investigate slow database queries, network latency, or resource contention. "
                            "Consider implementing caching or query optimization.",
                priority="high" if avg_deviation > 3 else "medium",
                related_anomalies=performance_anomalies,
                evidence={"average_deviation": avg_deviation, "affected_endpoints": len(set(
                    e.path for a in performance_anomalies for e in a.affected_entries if e.path
                ))}
            )
            insights.append(insight)

        # Reliability insights
        error_anomalies = [a for a in anomalies if a.anomaly_type in ["pattern", "sequence"] and
                          a.severity_level.value in ["HIGH", "CRITICAL"]]
        if error_anomalies:
            total_errors = sum(a.occurrence_count for a in error_anomalies)

            insight = Insight(
                category="reliability",
                title="Recurring Error Patterns Detected",
                description=f"Found {len(error_anomalies)} recurring error patterns with {total_errors} total occurrences.",
                recommendation="Review error logs for common root causes. "
                            "Implement error handling and monitoring for these patterns.",
                priority="high" if total_errors > 100 else "medium",
                related_anomalies=error_anomalies,
                evidence={"total_errors": total_errors, "unique_patterns": len(error_anomalies)}
            )
            insights.append(insight)

        # Security insights
        correlation_anomalies = [a for a in anomalies if "ip_errors" in a.pattern]
        if correlation_anomalies:
            insight = Insight(
                category="security",
                title="Suspicious Activity Detected",
                description=f"High error rate from specific IP addresses detected.",
                recommendation="Investigate potential attacks or abuse. "
                            "Consider rate limiting or blocking problematic IPs.",
                priority="high",
                related_anomalies=correlation_anomalies,
                evidence={"suspicious_ips": len(correlation_anomalies)}
            )
            insights.append(insight)

        # Volume insights
        volume_anomalies = [a for a in anomalies if a.context.get("metric") == "request_volume"]
        if volume_anomalies:
            max_rpm = max(a.context.get("requests_per_minute", 0) for a in volume_anomalies)

            insight = Insight(
                category="usage",
                title="Traffic Spike Detected",
                description=f"Unusual request volume detected. Peak: {max_rpm} requests/minute.",
                recommendation="Check for legitimate traffic increases or potential DDoS. "
                            "Ensure auto-scaling is configured.",
                priority="high" if max_rpm > 1000 else "medium",
                related_anomalies=volume_anomalies,
                evidence={"peak_rpm": max_rpm, "spike_count": len(volume_anomalies)}
            )
            insights.append(insight)

        return insights
