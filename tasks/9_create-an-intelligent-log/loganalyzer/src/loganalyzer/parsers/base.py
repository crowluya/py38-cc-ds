"""Base parser interface and common parsing utilities."""

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterator, List, Optional
from pathlib import Path

from ..models import LogEntry, LogLevel
from ..config import ParserConfig


class BaseParser(ABC):
    """Abstract base class for log parsers."""

    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize parser with configuration."""
        self.config = config or ParserConfig()
        self._line_number = 0

    @abstractmethod
    def parse_line(self, line: str, source: str = "") -> Optional[LogEntry]:
        """Parse a single log line into a LogEntry.

        Args:
            line: Raw log line
            source: Source file identifier

        Returns:
            LogEntry if parsing successful, None otherwise
        """
        pass

    def parse_file(self, file_path: str) -> Iterator[LogEntry]:
        """Parse a log file and yield LogEntry objects.

        Args:
            file_path: Path to log file

        Yields:
            LogEntry objects
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {file_path}")

        source = path.name

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                self._line_number += 1
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = self.parse_line(line, source)
                    if entry:
                        entry.line_number = self._line_number
                        entry.source = source
                        yield entry
                except Exception:
                    # Skip unparseable lines
                    continue

        # Reset line number for next file
        self._line_number = 0

    def parse_string(self, log_data: str, source: str = "string") -> Iterator[LogEntry]:
        """Parse log data from a string.

        Args:
            log_data: Log data as string
            source: Source identifier

        Yields:
            LogEntry objects
        """
        for line in log_data.split("\n"):
            self._line_number += 1
            line = line.strip()
            if not line:
                continue

            try:
                entry = self.parse_line(line, source)
                if entry:
                    entry.line_number = self._line_number
                    entry.source = source
                    yield entry
            except Exception:
                continue

        self._line_number = 0

    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string using configured formats.

        Args:
            timestamp_str: Timestamp string

        Returns:
            datetime object or None if parsing fails
        """
        for fmt in self.config.date_formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except (ValueError, TypeError):
                continue

        # Try Python's built-in dateutil as fallback
        try:
            from dateutil import parser as date_parser
            return date_parser.parse(timestamp_str)
        except Exception:
            return None

    def extract_level(self, message: str) -> LogLevel:
        """Extract log level from message.

        Args:
            message: Log message

        Returns:
            LogLevel
        """
        # Common patterns
        level_patterns = [
            r"\b(TRACE|DEBUG)\b",
            r"\b(INFO|INFORMATION)\b",
            r"\b(WARN|WARNING)\b",
            r"\b(ERROR|ERR|ERROR)\b",
            r"\b(CRITICAL|CRIT|FATAL|FATAL)\b",
        ]

        message_upper = message.upper()

        for pattern in level_patterns:
            match = re.search(pattern, message_upper)
            if match:
                return LogLevel.from_string(match.group(1))

        # Default to INFO
        return LogLevel.INFO


class RegexParser(BaseParser):
    """Parser based on regular expression patterns."""

    def __init__(self, pattern: str, config: Optional[ParserConfig] = None):
        """Initialize regex parser.

        Args:
            pattern: Regular expression pattern with named groups
            config: Parser configuration
        """
        super().__init__(config)
        self.pattern = re.compile(pattern)

    def parse_line(self, line: str, source: str = "") -> Optional[LogEntry]:
        """Parse line using regex pattern."""
        match = self.pattern.match(line)
        if not match:
            return None

        data = match.groupdict()

        # Extract required fields
        timestamp = self.parse_timestamp(data.get("timestamp", ""))
        if not timestamp:
            timestamp = datetime.now()

        message = data.get("message", "")
        level = self.extract_level(message)

        # Build log entry
        entry = LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            raw_line=line,
            line_number=self._line_number,
            source=source,
            ip=data.get("ip"),
            method=data.get("method"),
            path=data.get("path"),
            status_code=int(data["status_code"]) if data.get("status_code", "").isdigit() else None,
            response_size=int(data["size"]) if data.get("size", "").isdigit() else None,
            user_agent=data.get("user_agent"),
            referrer=data.get("referrer"),
        )

        return entry
