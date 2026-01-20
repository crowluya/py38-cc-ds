"""
Data models for pylint analysis results.

Defines the structure for storing and manipulating pylint analysis results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import IntEnum


class MessageType(IntEnum):
    """Pylint message type categories."""

    FATAL = 1
    ERROR = 2
    WARNING = 3
    CONVENTION = 4
    REFACTOR = 5
    INFO = 6

    @classmethod
    def from_string(cls, value: str) -> "MessageType":
        """Convert string to MessageType."""
        mapping = {
            "fatal": cls.FATAL,
            "error": cls.ERROR,
            "warning": cls.WARNING,
            "convention": cls.CONVENTION,
            "refactor": cls.REFACTOR,
            "info": cls.INFO,
        }
        return mapping.get(value.lower(), cls.INFO)

    def __str__(self) -> str:
        """String representation."""
        return self.name.capitalize()


@dataclass
class Issue:
    """Represents a single pylint issue/message."""

    # Issue identification
    msg_id: str  # e.g., "C0111", "W0613"
    symbol: str  # e.g., "missing-docstring", "unused-argument"
    message: str

    # Location information
    path: str
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    # Classification
    type: MessageType = MessageType.INFO
    category: str = ""  # e.g., "Convention", "Warning"

    # Context
    context: Optional[str] = None
    module: str = ""

    # Confidence (0-1)
    confidence: float = 1.0

    @property
    def severity(self) -> str:
        """Get severity level string."""
        if self.type in [MessageType.FATAL, MessageType.ERROR]:
            return "error"
        elif self.type == MessageType.WARNING:
            return "warning"
        else:
            return "info"

    @property
    def location_str(self) -> str:
        """Get formatted location string."""
        if self.end_line and self.end_line != self.line:
            return f"{self.path}:{self.line}:{self.column}-{self.end_line}:{self.end_column}"
        return f"{self.path}:{self.line}:{self.column}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary."""
        return {
            "msg_id": self.msg_id,
            "symbol": self.symbol,
            "message": self.message,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "type": str(self.type),
            "category": self.category,
            "context": self.context,
            "module": self.module,
            "confidence": self.confidence,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Issue":
        """Create Issue from dictionary."""
        return cls(
            msg_id=data["msg_id"],
            symbol=data["symbol"],
            message=data["message"],
            path=data["path"],
            line=data["line"],
            column=data["column"],
            end_line=data.get("end_line"),
            end_column=data.get("end_column"),
            type=MessageType.from_string(data.get("type", "info")),
            category=data.get("category", ""),
            context=data.get("context"),
            module=data.get("module", ""),
            confidence=data.get("confidence", 1.0),
        )

    @classmethod
    def from_pylint_dict(cls, data: Dict[str, Any]) -> "Issue":
        """Create Issue from pylint JSON output."""
        return cls(
            msg_id=data.get("message-id", ""),
            symbol=data.get("symbol", ""),
            message=data.get("message", ""),
            path=data.get("path", ""),
            line=data.get("line", 0),
            column=data.get("column", 0),
            end_line=data.get("endLine"),
            end_column=data.get("endColumn"),
            type=MessageType.from_string(data.get("type", "info")),
            category=data.get("category", ""),
            context=data.get("context"),
            module=data.get("module", ""),
            confidence=data.get("confidence", 1.0),
        )


@dataclass
class Metric:
    """Represents a code metric."""

    name: str
    value: float
    description: str = ""
    previous_value: Optional[float] = None

    @property
    def change(self) -> Optional[float]:
        """Calculate change from previous value."""
        if self.previous_value is None:
            return None
        return self.value - self.previous_value

    @property
    def percentage_change(self) -> Optional[float]:
        """Calculate percentage change from previous value."""
        if self.previous_value is None or self.previous_value == 0:
            return None
        return ((self.value - self.previous_value) / self.previous_value) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "previous_value": self.previous_value,
            "change": self.change,
            "percentage_change": self.percentage_change,
        }


@dataclass
class ModuleStats:
    """Statistics for a single module."""

    module: str
    path: str

    # Counts
    fatal: int = 0
    error: int = 0
    warning: int = 0
    convention: int = 0
    refactor: int = 0
    info: int = 0

    # Code metrics
    statements: int = 0
    lines_of_code: int = 0
    comment_lines: int = 0
    docstring_lines: int = 0

    # Score
    score: Optional[float] = None

    @property
    def total_issues(self) -> int:
        """Total number of issues."""
        return self.fatal + self.error + self.warning + self.convention + self.refactor + self.info

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "module": self.module,
            "path": self.path,
            "fatal": self.fatal,
            "error": self.error,
            "warning": self.warning,
            "convention": self.convention,
            "refactor": self.refactor,
            "info": self.info,
            "total_issues": self.total_issues,
            "statements": self.statements,
            "lines_of_code": self.lines_of_code,
            "comment_lines": self.comment_lines,
            "docstring_lines": self.docstring_lines,
            "score": self.score,
        }


@dataclass
class AnalysisResult:
    """Complete pylint analysis results."""

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    pylint_version: str = ""
    python_version: str = ""

    # Analysis scope
    paths_analyzed: List[str] = field(default_factory=list)
    files_analyzed: int = 0
    modules_analyzed: int = 0

    # Overall score
    global_score: Optional[float] = None

    # Issues
    issues: List[Issue] = field(default_factory=list)

    # Statistics by module
    module_stats: List[ModuleStats] = field(default_factory=list)

    # Global metrics
    metrics: List[Metric] = field(default_factory=list)

    # Execution info
    execution_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None

    def get_issues_by_type(self, message_type: MessageType) -> List[Issue]:
        """Get all issues of a specific type."""
        return [issue for issue in self.issues if issue.type == message_type]

    def get_issues_by_module(self, module: str) -> List[Issue]:
        """Get all issues for a specific module."""
        return [issue for issue in self.issues if issue.module == module]

    def get_issues_by_severity(self, severity: str) -> List[Issue]:
        """Get issues by severity (error, warning, info)."""
        return [issue for issue in self.issues if issue.severity == severity]

    @property
    def total_issues(self) -> int:
        """Total number of issues."""
        return len(self.issues)

    @property
    def fatal_count(self) -> int:
        """Count of fatal issues."""
        return sum(1 for issue in self.issues if issue.type == MessageType.FATAL)

    @property
    def error_count(self) -> int:
        """Count of error issues."""
        return sum(1 for issue in self.issues if issue.type == MessageType.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning issues."""
        return sum(1 for issue in self.issues if issue.type == MessageType.WARNING)

    @property
    def convention_count(self) -> int:
        """Count of convention issues."""
        return sum(1 for issue in self.issues if issue.type == MessageType.CONVENTION)

    @property
    def refactor_count(self) -> int:
        """Count of refactor issues."""
        return sum(1 for issue in self.issues if issue.type == MessageType.REFACTOR)

    @property
    def info_count(self) -> int:
        """Count of info issues."""
        return sum(1 for issue in self.issues if issue.type == MessageType.INFO)

    @property
    def has_errors(self) -> bool:
        """Whether analysis found any errors or fatal issues."""
        return self.fatal_count > 0 or self.error_count > 0

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of results."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "global_score": self.global_score,
            "total_issues": self.total_issues,
            "fatal": self.fatal_count,
            "error": self.error_count,
            "warning": self.warning_count,
            "convention": self.convention_count,
            "refactor": self.refactor_count,
            "info": self.info_count,
            "files_analyzed": self.files_analyzed,
            "modules_analyzed": self.modules_analyzed,
            "execution_time": self.execution_time,
            "success": self.success,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "pylint_version": self.pylint_version,
            "python_version": self.python_version,
            "paths_analyzed": self.paths_analyzed,
            "files_analyzed": self.files_analyzed,
            "modules_analyzed": self.modules_analyzed,
            "global_score": self.global_score,
            "issues": [issue.to_dict() for issue in self.issues],
            "module_stats": [stat.to_dict() for stat in self.module_stats],
            "metrics": [metric.to_dict() for metric in self.metrics],
            "execution_time": self.execution_time,
            "success": self.success,
            "error_message": self.error_message,
            "summary": self.get_summary(),
        }
