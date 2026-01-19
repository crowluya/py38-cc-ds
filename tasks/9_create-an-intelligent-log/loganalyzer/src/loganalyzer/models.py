"""Core data models for LogAnalyzer."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """Convert string to LogLevel."""
        level_map = {
            "DEBUG": cls.DEBUG,
            "INFO": cls.INFO,
            "WARN": cls.WARNING,
            "WARNING": cls.WARNING,
            "ERROR": cls.ERROR,
            "ERR": cls.ERROR,
            "CRITICAL": cls.CRITICAL,
            "CRIT": cls.CRITICAL,
            "FATAL": cls.CRITICAL,
        }
        return level_map.get(level.upper(), cls.INFO)

    def __str__(self) -> str:
        return self.name


class SeverityLevel(Enum):
    """Severity levels for anomalies."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Represents a single log entry."""

    timestamp: datetime
    level: LogLevel
    message: str
    raw_line: str
    line_number: int
    source: str = ""

    # Optional fields that may be present in some log formats
    ip: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    response_size: Optional[int] = None
    response_time: Optional[float] = None
    user_agent: Optional[str] = None
    referrer: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "message": self.message,
            "line_number": self.line_number,
            "source": self.source,
            "ip": self.ip,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "response_size": self.response_size,
            "response_time": self.response_time,
            "user_agent": self.user_agent,
            "referrer": self.referrer,
            "extra": self.extra,
        }


@dataclass
class Anomaly:
    """Represents a detected anomaly."""

    anomaly_type: str  # "statistical", "pattern", "spike", "sequence", etc.
    severity: float  # 0-10 score
    severity_level: SeverityLevel
    description: str
    confidence: float  # 0-1
    affected_entries: List[LogEntry]
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int

    # Statistical data for statistical anomalies
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    deviation: Optional[float] = None
    z_score: Optional[float] = None

    # Pattern data for pattern anomalies
    pattern: Optional[str] = None
    pattern_frequency: Optional[int] = None

    # Contextual information
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Calculate duration of anomaly in seconds."""
        if self.first_seen and self.last_seen:
            return (self.last_seen - self.first_seen).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.anomaly_type,
            "severity": self.severity,
            "severity_level": self.severity_level.value,
            "description": self.description,
            "confidence": self.confidence,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "duration_seconds": self.duration,
            "occurrence_count": self.occurrence_count,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "deviation": self.deviation,
            "z_score": self.z_score,
            "pattern": self.pattern,
            "pattern_frequency": self.pattern_frequency,
            "context": self.context,
            "affected_entry_count": len(self.affected_entries),
            "sample_entries": [e.to_dict() for e in self.affected_entries[:5]],
        }


@dataclass
class Insight:
    """Represents an actionable insight derived from analysis."""

    category: str  # "performance", "security", "reliability", "usage", etc.
    title: str
    description: str
    recommendation: str
    priority: str  # "immediate", "high", "medium", "low"
    related_anomalies: List[Anomaly]
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "priority": self.priority,
            "related_anomaly_count": len(self.related_anomalies),
            "evidence": self.evidence,
        }


@dataclass
class AnalysisResult:
    """Container for complete analysis results."""

    source_file: str
    total_entries: int
    analyzed_entries: int
    start_time: datetime
    end_time: datetime

    # Statistics
    log_level_counts: Dict[str, int] = field(default_factory=dict)
    error_rate: float = 0.0
    average_response_time: Optional[float] = None
    total_response_size: Optional[int] = None

    # Analysis results
    anomalies: List[Anomaly] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)

    # Filtering info
    filters_applied: Dict[str, Any] = field(default_factory=dict)

    # Performance metrics
    analysis_duration: float = 0.0

    @property
    def anomaly_count(self) -> int:
        return len(self.anomalies)

    @property
    def insight_count(self) -> int:
        return len(self.insights)

    @property
    def critical_anomalies(self) -> List[Anomaly]:
        return [a for a in self.anomalies if a.severity_level == SeverityLevel.CRITICAL]

    @property
    def high_severity_anomalies(self) -> List[Anomaly]:
        return [a for a in self.anomalies if a.severity_level in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]]

    def get_anomalies_by_type(self, anomaly_type: str) -> List[Anomaly]:
        """Get anomalies filtered by type."""
        return [a for a in self.anomalies if a.anomaly_type == anomaly_type]

    def get_anomalies_by_severity(self, min_severity: float) -> List[Anomaly]:
        """Get anomalies with severity >= min_severity."""
        return [a for a in self.anomalies if a.severity >= min_severity]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_file": self.source_file,
            "total_entries": self.total_entries,
            "analyzed_entries": self.analyzed_entries,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "analysis_duration_seconds": self.analysis_duration,
            "statistics": {
                "log_level_counts": self.log_level_counts,
                "error_rate": self.error_rate,
                "average_response_time": self.average_response_time,
                "total_response_size": self.total_response_size,
            },
            "anomalies": {
                "total": self.anomaly_count,
                "critical": len(self.critical_anomalies),
                "high_severity": len(self.high_severity_anomalies),
                "by_type": {
                    atype: len(self.get_anomalies_by_type(atype))
                    for atype in set(a.anomaly_type for a in self.anomalies)
                },
                "details": [a.to_dict() for a in self.anomalies],
            },
            "insights": {
                "total": self.insight_count,
                "details": [i.to_dict() for i in self.insights],
            },
            "filters_applied": self.filters_applied,
        }


@dataclass
class FilterConfig:
    """Configuration for filtering log entries."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_level: Optional[LogLevel] = None
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    min_severity: Optional[float] = None

    def matches(self, entry: LogEntry) -> bool:
        """Check if a log entry matches all filter criteria."""
        # Time filter
        if self.start_time and entry.timestamp < self.start_time:
            return False
        if self.end_time and entry.timestamp > self.end_time:
            return False

        # Level filter
        if self.min_level and entry.level.value < self.min_level.value:
            return False

        # Include patterns
        if self.include_patterns:
            if not any(pattern in entry.message for pattern in self.include_patterns):
                return False

        # Exclude patterns
        if any(pattern in entry.message for pattern in self.exclude_patterns):
            return False

        return True
