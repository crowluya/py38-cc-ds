"""JSON log format parser."""

import json
from datetime import datetime
from typing import Optional

from .base import BaseParser
from ..models import LogEntry, LogLevel
from ..config import ParserConfig


class JSONParser(BaseParser):
    """Parser for JSON-formatted logs.

    Example formats:
        {"timestamp": "2023-10-10T13:55:36Z", "level": "ERROR", "message": "Database connection failed"}
        {"time": "2023-10-10T13:55:36+00:00", "severity": "WARNING", "msg": "High memory usage"}
    """

    # Common timestamp field names
    TIMESTAMP_FIELDS = ["timestamp", "time", "@timestamp", "datetime", "date", "created_at"]

    # Common level field names
    LEVEL_FIELDS = ["level", "severity", "priority", "log_level", "loglevel"]

    # Common message field names
    MESSAGE_FIELDS = ["message", "msg", "text", "description", "error"]

    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize JSON parser."""
        super().__init__(config)

    def parse_line(self, line: str, source: str = "") -> Optional[LogEntry]:
        """Parse JSON log line."""
        line = line.strip()
        if not line.startswith("{"):
            return None

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        # Extract timestamp
        timestamp = self._extract_timestamp(data)
        if not timestamp:
            timestamp = datetime.now()

        # Extract log level
        level = self._extract_level(data)

        # Extract message
        message = self._extract_message(data)

        # Extract common fields
        entry = LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            raw_line=line,
            line_number=self._line_number,
            source=source,
            ip=data.get("ip", data.get("remote_addr", data.get("client_ip"))),
            method=data.get("method", data.get("request_method")),
            path=data.get("path", data.get("request_uri", data.get("url"))),
            status_code=data.get("status_code", data.get("status", data.get("code"))),
            response_size=data.get("size", data.get("response_size", data.get("bytes"))),
            response_time=data.get("response_time", data.get("duration", data.get("rt"))),
            user_agent=data.get("user_agent", data.get("ua", data.get("http_user_agent"))),
            referrer=data.get("referrer", data.get("referer", data.get("http_referer"))),
            extra={k: v for k, v in data.items()
                   if k not in {*self.TIMESTAMP_FIELDS, *self.LEVEL_FIELDS,
                                *self.MESSAGE_FIELDS, "ip", "remote_addr", "client_ip",
                                "method", "request_method", "path", "request_uri", "url",
                                "status_code", "status", "code", "size", "response_size",
                                "bytes", "response_time", "duration", "rt", "user_agent",
                                "ua", "http_user_agent", "referrer", "referer", "http_referer"}}
        )

        return entry

    def _extract_timestamp(self, data: dict) -> Optional[datetime]:
        """Extract timestamp from JSON data."""
        for field in self.TIMESTAMP_FIELDS:
            if field in data:
                timestamp = self.parse_timestamp(str(data[field]))
                if timestamp:
                    return timestamp
        return None

    def _extract_level(self, data: dict) -> LogLevel:
        """Extract log level from JSON data."""
        for field in self.LEVEL_FIELDS:
            if field in data:
                try:
                    return LogLevel.from_string(str(data[field]))
                except (ValueError, KeyError):
                    continue

        # Try to infer from status code
        if "status" in data or "status_code" in data:
            status = data.get("status") or data.get("status_code")
            if isinstance(status, int):
                if status >= 500:
                    return LogLevel.ERROR
                elif status >= 400:
                    return LogLevel.WARNING

        return LogLevel.INFO

    def _extract_message(self, data: dict) -> str:
        """Extract message from JSON data."""
        for field in self.MESSAGE_FIELDS:
            if field in data:
                msg = data[field]
                if isinstance(msg, str):
                    return msg

        # Fallback: construct from available fields
        parts = []
        if "error" in data:
            parts.append(str(data["error"]))
        if "exception" in data:
            parts.append(str(data["exception"]))

        return " ".join(parts) if parts else "JSON log entry"
