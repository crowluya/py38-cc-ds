"""Apache log format parsers."""

import re
from typing import Optional

from .base import BaseParser
from ..models import LogEntry, LogLevel
from ..config import ParserConfig


class ApacheParser(BaseParser):
    """Parser for Apache Common Log Format and Combined Log Format.

    Common Log Format:
        127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/users HTTP/1.1" 200 2326

    Combined Log Format:
        127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/users HTTP/1.1" 200 2326 "http://example.com" "Mozilla/5.0"
    """

    # Common Log Format pattern
    CLF_PATTERN = re.compile(
        r'^(?P<ip>\S+) '
        r'\S+ '  # identd (usually -)
        r'\S+ '  # userid (usually -)
        r'\[(?P<timestamp>[^\]]+)\] '
        r'"(?P<request>\S+ \S+ \S+)" '
        r'(?P<status_code>\d+) '
        r'(?P<size>\d+|-)'
    )

    # Combined Log Format pattern
    COMBINED_PATTERN = re.compile(
        r'^(?P<ip>\S+) '
        r'\S+ '  # identd
        r'\S+ '  # userid
        r'\[(?P<timestamp>[^\]]+)\] '
        r'"(?P<request>\S+ \S+ \S+)" '
        r'(?P<status_code>\d+) '
        r'(?P<size>\d+|-) '
        r'"(?P<referrer>[^"]*)" '
        r'"(?P<user_agent>[^"]*)"'
    )

    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize Apache parser."""
        super().__init__(config)

    def parse_line(self, line: str, source: str = "") -> Optional[LogEntry]:
        """Parse Apache log line."""
        # Try Combined format first (more specific)
        match = self.COMBINED_PATTERN.match(line)
        if not match:
            # Try Common format
            match = self.CLF_PATTERN.match(line)

        if not match:
            return None

        data = match.groupdict()

        # Parse timestamp
        timestamp = self.parse_timestamp(data["timestamp"])
        if not timestamp:
            return None

        # Parse request (METHOD PATH PROTOCOL)
        request = data.get("request", "")
        parts = request.split()
        method = parts[0] if len(parts) > 0 else None
        path = parts[1] if len(parts) > 1 else None

        # Parse status code
        try:
            status_code = int(data["status_code"])
        except (ValueError, KeyError):
            status_code = None

        # Parse size
        size_str = data.get("size", "0")
        size = None if size_str == "-" else int(size_str)

        # Determine log level from status code
        if status_code:
            if status_code >= 500:
                level = LogLevel.ERROR
            elif status_code >= 400:
                level = LogLevel.WARNING
            else:
                level = LogLevel.INFO
        else:
            level = LogLevel.INFO

        # Build message
        message = f"{method} {path} - {status_code}" if method and path else str(status_code)

        # Create log entry
        entry = LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            raw_line=line,
            line_number=self._line_number,
            source=source,
            ip=data.get("ip"),
            method=method,
            path=path,
            status_code=status_code,
            response_size=size,
            user_agent=data.get("user_agent"),
            referrer=data.get("referrer"),
        )

        return entry


class ApacheErrorParser(BaseParser):
    """Parser for Apache error logs.

    Format:
        [Wed Oct 11 14:32:52 2000] [error] [client 127.0.0.1] Client sent malformed Host header
        [Wed Oct 11 14:32:52 2000] [warn] [client 127.0.0.1] mod_foo: Foo happened
    """

    ERROR_PATTERN = re.compile(
        r'^\[(?P<timestamp>[^\]]+)\] '
        r'\[(?P<level>\w+)\] '
        r'(?:\[client (?P<ip>\S+)\] )?'
        r'(?P<message>.*)'
    )

    def parse_line(self, line: str, source: str = "") -> Optional[LogEntry]:
        """Parse Apache error log line."""
        match = self.ERROR_PATTERN.match(line)
        if not match:
            return None

        data = match.groupdict()

        # Parse timestamp
        timestamp = self.parse_timestamp(data["timestamp"])
        if not timestamp:
            return None

        # Parse level
        level_str = data.get("level", "info")
        level = LogLevel.from_string(level_str)

        # Create log entry
        entry = LogEntry(
            timestamp=timestamp,
            level=level,
            message=data["message"],
            raw_line=line,
            line_number=self._line_number,
            source=source,
            ip=data.get("ip"),
        )

        return entry
