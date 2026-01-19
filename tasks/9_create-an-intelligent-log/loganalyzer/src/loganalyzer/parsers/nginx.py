"""Nginx log format parsers."""

import re
from typing import Optional

from .base import BaseParser
from ..models import LogEntry, LogLevel
from ..config import ParserConfig


class NginxParser(BaseParser):
    """Parser for Nginx access logs.

    Nginx default format is similar to Apache Combined Log Format:
        127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/status HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0"
    """

    # Nginx default format (similar to Apache Combined)
    DEFAULT_PATTERN = re.compile(
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

    # Nginx JSON format (for custom JSON logs)
    JSON_PATTERN = re.compile(r'^\{.*\}$')

    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize Nginx parser."""
        super().__init__(config)

    def parse_line(self, line: str, source: str = "") -> Optional[LogEntry]:
        """Parse Nginx log line."""
        # Check for JSON format first
        if self.JSON_PATTERN.match(line.strip()):
            return self._parse_json_line(line, source)

        # Try default format
        match = self.DEFAULT_PATTERN.match(line)
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

    def _parse_json_line(self, line: str, source: str = "") -> Optional[LogEntry]:
        """Parse Nginx JSON log line."""
        try:
            import json
            data = json.loads(line)

            # Extract timestamp
            timestamp = None
            for ts_key in ["time", "timestamp", "time_local", "@timestamp"]:
                if ts_key in data:
                    timestamp = self.parse_timestamp(str(data[ts_key]))
                    if timestamp:
                        break

            if not timestamp:
                timestamp = datetime.now()

            # Extract log level
            level = LogLevel.INFO
            if "level" in data:
                level = LogLevel.from_string(data["level"])
            elif "status" in data:
                status = data["status"]
                if status >= 500:
                    level = LogLevel.ERROR
                elif status >= 400:
                    level = LogLevel.WARNING

            # Build message
            message = data.get("message", data.get("request", ""))

            # Create log entry
            entry = LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                raw_line=line,
                line_number=self._line_number,
                source=source,
                ip=data.get("remote_addr", data.get("ip")),
                method=data.get("request_method"),
                path=data.get("request_uri"),
                status_code=data.get("status"),
                response_size=data.get("body_bytes_sent"),
                response_time=data.get("request_time"),
                user_agent=data.get("http_user_agent"),
                referrer=data.get("http_referer"),
                extra=data,
            )

            return entry

        except Exception:
            return None
