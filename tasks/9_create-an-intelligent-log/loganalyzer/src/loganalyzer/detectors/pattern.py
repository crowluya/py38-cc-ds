"""Pattern-based anomaly detection."""

import re
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher

from ..models import LogEntry, Anomaly, SeverityLevel, LogLevel
from ..config import AnalysisConfig


class PatternDetector:
    """Pattern-based anomaly detector."""

    def __init__(self, config: AnalysisConfig):
        """Initialize pattern detector.

        Args:
            config: Analysis configuration
        """
        self.config = config

    def detect(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect pattern-based anomalies.

        Args:
            entries: List of log entries

        Returns:
            List of detected anomalies
        """
        if not entries:
            return []

        anomalies = []

        # Detect frequent error patterns
        error_patterns = self._detect_error_patterns(entries)
        anomalies.extend(error_patterns)

        # Detect new/unknown patterns
        new_patterns = self._detect_new_patterns(entries)
        anomalies.extend(new_patterns)

        # Detect repeated failures
        repeated_failures = self._detect_repeated_failures(entries)
        anomalies.extend(repeated_failures)

        # Detect correlation patterns (co-occurring errors)
        correlations = self._detect_correlations(entries)
        anomalies.extend(correlations)

        return anomalies

    def _detect_error_patterns(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect frequent error patterns."""
        # Extract error messages
        error_entries = [e for e in entries if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]]

        if not error_entries:
            return []

        # Normalize error messages (remove numbers, IPs, etc.)
        normalized_messages = []
        for entry in error_entries:
            normalized = self._normalize_message(entry.message)
            normalized_messages.append((entry, normalized))

        # Count patterns
        pattern_counts = Counter(normalized for _, normalized in normalized_messages)

        anomalies = []
        for pattern, count in pattern_counts.most_common(20):
            if count >= self.config.min_pattern_frequency:
                # Find all entries with this pattern
                affected_entries = [e for e, norm in normalized_messages if norm == pattern]

                # Calculate severity based on frequency
                severity = min(10, 3 + (count / len(error_entries)) * 7)
                severity_level = self._get_severity_level(severity)

                anomaly = Anomaly(
                    anomaly_type="pattern",
                    severity=severity,
                    severity_level=severity_level,
                    description=f"Recurring error pattern: '{pattern[:100]}...' ({count} occurrences)",
                    confidence=min(1.0, count / len(error_entries) * 2),
                    affected_entries=affected_entries[:50],  # Limit sample
                    first_seen=min(e.timestamp for e in affected_entries),
                    last_seen=max(e.timestamp for e in affected_entries),
                    occurrence_count=count,
                    pattern=pattern,
                    pattern_frequency=count,
                    context={"pattern_type": "error", "sample_message": affected_entries[0].message if affected_entries else ""}
                )

                anomalies.append(anomaly)

        return anomalies

    def _detect_new_patterns(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect sudden appearance of new patterns."""
        if len(entries) < self.config.baseline_window:
            return []

        # Split into baseline and current
        split_point = len(entries) // 2
        baseline_entries = entries[:split_point]
        current_entries = entries[split_point:]

        # Get patterns in baseline
        baseline_patterns = set()
        for entry in baseline_entries:
            normalized = self._normalize_message(entry.message)
            baseline_patterns.add(normalized)

        # Find new patterns in current
        new_pattern_entries = []
        for entry in current_entries:
            normalized = self._normalize_message(entry.message)
            if normalized not in baseline_patterns and entry.level in [LogLevel.ERROR, LogLevel.WARNING]:
                new_pattern_entries.append(entry)

        if new_pattern_entries:
            # Group by pattern
            pattern_groups = defaultdict(list)
            for entry in new_pattern_entries:
                normalized = self._normalize_message(entry.message)
                pattern_groups[normalized].append(entry)

            anomalies = []
            for pattern, affected in pattern_groups.items():
                if len(affected) >= 3:  # At least 3 occurrences
                    severity = min(10, 6 + len(affected) / 10)
                    severity_level = self._get_severity_level(severity)

                    anomaly = Anomaly(
                        anomaly_type="pattern",
                        severity=severity,
                        severity_level=severity_level,
                        description=f"New error pattern emerged: '{pattern[:100]}...'",
                        confidence=0.8,
                        affected_entries=affected[:20],
                        first_seen=min(e.timestamp for e in affected),
                        last_seen=max(e.timestamp for e in affected),
                        occurrence_count=len(affected),
                        pattern=pattern,
                        pattern_frequency=len(affected),
                        context={"pattern_type": "new", "first_seen": min(e.timestamp for e in affected)}
                    )

                    anomalies.append(anomaly)

            return anomalies

        return []

    def _detect_repeated_failures(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect repeated failure sequences."""
        # Look for consecutive errors
        consecutive_errors = []
        current_sequence = []

        for entry in entries:
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                current_sequence.append(entry)
            else:
                if len(current_sequence) >= 5:  # At least 5 consecutive errors
                    consecutive_errors.append(current_sequence[:])
                current_sequence = []

        # Don't forget the last sequence
        if len(current_sequence) >= 5:
            consecutive_errors.append(current_sequence)

        anomalies = []
        for sequence in consecutive_errors:
            # Check if they're related (similar messages)
            messages = [e.message for e in sequence]
            similarity = self._calculate_similarity(messages)

            if similarity > 0.5:  # 50% similar
                severity = min(10, 6 + len(sequence) / 5)
                severity_level = self._get_severity_level(severity)

                anomaly = Anomaly(
                    anomaly_type="sequence",
                    severity=severity,
                    severity_level=severity_level,
                    description=f"Repeated failure sequence: {len(sequence)} consecutive errors",
                    confidence=similarity,
                    affected_entries=sequence[:50],
                    first_seen=sequence[0].timestamp,
                    last_seen=sequence[-1].timestamp,
                    occurrence_count=len(sequence),
                    pattern="consecutive_errors",
                    pattern_frequency=len(sequence),
                    context={"sequence_length": len(sequence), "similarity": similarity}
                )

                anomalies.append(anomaly)

        return anomalies

    def _detect_correlations(self, entries: List[LogEntry]) -> List[Anomaly]:
        """Detect correlated events (co-occurring errors)."""
        # Look for IP addresses with multiple errors
        error_by_ip = defaultdict(list)
        for entry in entries:
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL] and entry.ip:
                error_by_ip[entry.ip].append(entry)

        anomalies = []
        for ip, ip_errors in error_by_ip.items():
            if len(ip_errors) >= 10:  # IP with 10+ errors
                # Check if errors are diverse
                error_types = set(self._normalize_message(e.message) for e in ip_errors)

                severity = min(10, 5 + len(ip_errors) / 10)
                severity_level = self._get_severity_level(severity)

                anomaly = Anomaly(
                    anomaly_type="pattern",
                    severity=severity,
                    severity_level=severity_level,
                    description=f"High error rate from IP {ip}: {len(ip_errors)} errors across {len(error_types)} patterns",
                    confidence=0.7,
                    affected_entries=ip_errors[:50],
                    first_seen=min(e.timestamp for e in ip_errors),
                    last_seen=max(e.timestamp for e in ip_errors),
                    occurrence_count=len(ip_errors),
                    pattern=f"ip_errors:{ip}",
                    pattern_frequency=len(ip_errors),
                    context={"ip": ip, "unique_error_types": len(error_types)}
                )

                anomalies.append(anomaly)

        return anomalies

    def _normalize_message(self, message: str) -> str:
        """Normalize message for pattern matching.

        Removes:
        - Numbers
        - IP addresses
        - UUIDs
        - Timestamps
        - File paths
        """
        # Replace IP addresses
        normalized = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '<IP>', message)

        # Replace numbers
        normalized = re.sub(r'\b\d+\b', '<NUM>', normalized)

        # Replace UUIDs
        normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                          '<UUID>', normalized, flags=re.IGNORECASE)

        # Replace file paths
        normalized = re.sub(r'/[/\w\.-]+', '<PATH>', normalized)
        normalized = re.sub(r'[A-Za-z]:\\[\w\\.-]+', '<PATH>', normalized)

        # Replace hex codes
        normalized = re.sub(r'0x[0-9a-f]+', '<HEX>', normalized, flags=re.IGNORECASE)

        # Convert to lowercase and strip
        normalized = normalized.lower().strip()

        return normalized

    def _calculate_similarity(self, strings: List[str]) -> float:
        """Calculate average similarity between strings."""
        if len(strings) < 2:
            return 1.0

        similarities = []
        for i in range(len(strings)):
            for j in range(i + 1, len(strings)):
                sim = SequenceMatcher(None, strings[i], strings[j]).ratio()
                similarities.append(sim)

        return sum(similarities) / len(similarities) if similarities else 0.0

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
