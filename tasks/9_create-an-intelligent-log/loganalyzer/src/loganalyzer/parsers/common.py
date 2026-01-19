"""Common parser utilities and format detection."""

import json
from typing import Optional, List
from pathlib import Path

from .base import BaseParser
from .apache import ApacheParser, ApacheErrorParser
from .nginx import NginxParser
from .json_parser import JSONParser
from ..config import ParserConfig


class LogFormat:
    """Supported log formats."""

    APACHE = "apache"
    APACHE_ERROR = "apache_error"
    NGINX = "nginx"
    JSON = "json"
    AUTO = "auto"


def detect_format(file_path: str, sample_lines: int = 10) -> str:
    """Detect log format from file sample.

    Args:
        file_path: Path to log file
        sample_lines: Number of lines to sample

    Returns:
        Detected format name
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {file_path}")

    # Collect sample lines
    samples = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= sample_lines:
                break
            line = line.strip()
            if line:
                samples.append(line)

    if not samples:
        return LogFormat.APACHE  # Default

    # Check for JSON format
    json_count = sum(1 for line in samples if line.startswith("{"))
    if json_count > len(samples) * 0.5:  # 50% or more are JSON
        return LogFormat.JSON

    # Check for Apache error log format
    apache_error_count = 0
    for line in samples:
        if '] [' in line and '] [client ' in line:
            apache_error_count += 1
    if apache_error_count > len(samples) * 0.3:
        return LogFormat.APACHE_ERROR

    # Check for Apache/Nginx combined format
    # Pattern: IP - - [timestamp] "METHOD PATH PROTOCOL" status size
    combined_count = 0
    for line in samples:
        parts = line.split('"')
        if len(parts) >= 2:
            if '] "' in line and parts[0].count(']') >= 1:
                combined_count += 1

    if combined_count > len(samples) * 0.5:
        # Could be Apache or Nginx - check for specific patterns
        # For simplicity, default to Apache (Nginx can parse Apache format)
        return LogFormat.APACHE

    # Default to Apache
    return LogFormat.APACHE


def create_parser(format_name: str, config: Optional[ParserConfig] = None) -> BaseParser:
    """Create parser instance for specified format.

    Args:
        format_name: Format name (auto, apache, nginx, json, etc.)
        config: Parser configuration

    Returns:
        Parser instance

    Raises:
        ValueError: If format is not supported
    """
    parsers = {
        LogFormat.APACHE: ApacheParser,
        LogFormat.APACHE_ERROR: ApacheErrorParser,
        LogFormat.NGINX: NginxParser,
        LogFormat.JSON: JSONParser,
    }

    format_name = format_name.lower()
    if format_name not in parsers:
        raise ValueError(f"Unsupported format: {format_name}. "
                        f"Supported formats: {', '.join(parsers.keys())}")

    parser_class = parsers[format_name]
    return parser_class(config)


def auto_detect_parser(file_path: str, config: Optional[ParserConfig] = None) -> BaseParser:
    """Auto-detect format and create appropriate parser.

    Args:
        file_path: Path to log file
        config: Parser configuration

    Returns:
        Parser instance
    """
    detected_format = detect_format(file_path)
    return create_parser(detected_format, config)


def is_compressed(file_path: str) -> bool:
    """Check if file is compressed.

    Args:
        file_path: Path to file

    Returns:
        True if file appears to be compressed
    """
    path = Path(file_path)
    extensions = {".gz", ".bz2", ".xz", ".zip", ".zst"}
    return any(path.name.lower().endswith(ext) for ext in extensions)


def get_files_from_path(input_path: str, recursive: bool = False) -> List[str]:
    """Get list of log files from path.

    Args:
        input_path: Path to file or directory
        recursive: Recursively search directories

    Returns:
        List of file paths
    """
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Path not found: {input_path}")

    if path.is_file():
        return [str(path)]

    if path.is_dir():
        pattern = "**/*" if recursive else "*"
        files = []

        for ext in [".log", ".txt", ".json"]:
            files.extend(path.glob(f"{pattern}{ext}"))

        # Also include files without extensions
        for f in path.glob(pattern):
            if f.is_file() and not f.name.startswith("."):
                if "." not in f.name or f.suffix == "":
                    files.append(f)

        return sorted(set(str(f) for f in files))

    return []
