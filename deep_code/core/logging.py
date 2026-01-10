"""
Unified Logging System (T023)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Centralized logging configuration
- File and console handlers
- Log rotation support
- Contextual logging
- Helper functions for common logging patterns
"""

import logging
import logging.handlers
import os
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union


# Package root logger name
ROOT_LOGGER_NAME = "deep_code"

# Thread-local storage for context
_context_local = threading.local()


class DeepCodeFormatter(logging.Formatter):
    """
    Custom formatter for DeepCode logs.

    Format: [TIMESTAMP] LEVEL [MODULE] MESSAGE
    """

    DEFAULT_FORMAT = "[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s"
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # Level colors for console output
    LEVEL_COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        use_color: bool = False,
        include_context: bool = False,
    ) -> None:
        """
        Initialize formatter.

        Args:
            fmt: Log format string
            datefmt: Date format string
            use_color: Whether to use colors
            include_context: Whether to include context data
        """
        super().__init__(
            fmt=fmt or self.DEFAULT_FORMAT,
            datefmt=datefmt or self.DEFAULT_DATE_FORMAT,
        )
        self._use_color = use_color
        self._include_context = include_context

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        # Add color if enabled
        if self._use_color and record.levelno in self.LEVEL_COLORS:
            record.levelname = (
                f"{self.LEVEL_COLORS[record.levelno]}"
                f"{record.levelname}"
                f"{self.RESET}"
            )

        # Format the base message
        formatted = super().format(record)

        # Add context if available and enabled
        if self._include_context:
            context = getattr(record, "context", None)
            if context:
                context_str = " ".join(f"{k}={v}" for k, v in context.items())
                formatted = f"{formatted} [{context_str}]"

        return formatted


class LevelFilter(logging.Filter):
    """Filter logs by minimum level."""

    def __init__(self, min_level: int = logging.DEBUG) -> None:
        """
        Initialize filter.

        Args:
            min_level: Minimum log level to allow
        """
        super().__init__()
        self._min_level = min_level

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter the record."""
        return record.levelno >= self._min_level


class ModuleFilter(logging.Filter):
    """Filter logs by module name."""

    def __init__(self, allowed_modules: Optional[List[str]] = None) -> None:
        """
        Initialize filter.

        Args:
            allowed_modules: List of allowed module prefixes
        """
        super().__init__()
        self._allowed = set(allowed_modules or [])

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter the record."""
        if not self._allowed:
            return True

        for prefix in self._allowed:
            if record.name.startswith(prefix):
                return True

        return False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given name.

    Args:
        name: Logger name (will be prefixed with 'deep_code.' if not already)

    Returns:
        Logger instance
    """
    if not name.startswith(ROOT_LOGGER_NAME):
        name = f"{ROOT_LOGGER_NAME}.{name}"

    return logging.getLogger(name)


def setup_logging(
    level: Union[str, int] = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
    use_color: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    format_string: Optional[str] = None,
) -> None:
    """
    Setup logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        console: Whether to log to console
        use_color: Whether to use colors in console
        max_bytes: Max bytes per log file (for rotation)
        backup_count: Number of backup files to keep
        format_string: Custom format string
    """
    # Convert string level to int
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger for deep_code
    root_logger = logging.getLogger(ROOT_LOGGER_NAME)
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers = []

    # Create formatters
    console_formatter = DeepCodeFormatter(
        fmt=format_string,
        use_color=use_color and _supports_color(),
    )
    file_formatter = DeepCodeFormatter(
        fmt=format_string,
        use_color=False,
    )

    # Add console handler
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Add file handler
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def _supports_color() -> bool:
    """Check if terminal supports colors."""
    if sys.platform == "win32":
        try:
            import colorama
            return True
        except ImportError:
            return False

    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


@contextmanager
def log_context(**kwargs: Any):
    """
    Context manager for adding context to log messages.

    Args:
        **kwargs: Context key-value pairs

    Example:
        with log_context(tool="Read", file="/test.txt"):
            logger.info("Processing file")
    """
    # Store context in thread-local storage
    if not hasattr(_context_local, "stack"):
        _context_local.stack = []

    _context_local.stack.append(kwargs)

    try:
        yield
    finally:
        _context_local.stack.pop()


def get_current_context() -> Dict[str, Any]:
    """
    Get current logging context.

    Returns:
        Merged context from all active context managers
    """
    if not hasattr(_context_local, "stack"):
        return {}

    merged = {}
    for ctx in _context_local.stack:
        merged.update(ctx)

    return merged


# ===== Helper Functions =====


def log_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    level: int = logging.DEBUG,
) -> None:
    """
    Log a tool call.

    Args:
        tool_name: Name of the tool
        arguments: Tool arguments
        level: Log level
    """
    logger = get_logger("tools")

    # Truncate large arguments
    args_str = _truncate_dict(arguments, max_value_len=100)

    logger.log(level, "Tool call: %s(%s)", tool_name, args_str)


def log_tool_result(
    tool_name: str,
    result: Any,
    level: int = logging.DEBUG,
) -> None:
    """
    Log a tool result.

    Args:
        tool_name: Name of the tool
        result: Tool result
        level: Log level
    """
    logger = get_logger("tools")

    success = getattr(result, "success", True)
    output = getattr(result, "output", str(result))

    # Truncate output
    if len(output) > 200:
        output = output[:200] + "..."

    status = "success" if success else "failed"
    logger.log(level, "Tool result: %s [%s] %s", tool_name, status, output)


def log_llm_call(
    model: str,
    messages: List[Dict[str, Any]],
    tokens: Optional[int] = None,
    level: int = logging.DEBUG,
) -> None:
    """
    Log an LLM call.

    Args:
        model: Model name
        messages: Messages sent to LLM
        tokens: Token count (if available)
        level: Log level
    """
    logger = get_logger("llm")

    msg_count = len(messages)
    token_str = f", tokens={tokens}" if tokens else ""

    logger.log(level, "LLM call: model=%s, messages=%d%s", model, msg_count, token_str)


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: int = logging.ERROR,
) -> None:
    """
    Log an error with context.

    Args:
        error: Exception to log
        context: Additional context
        level: Log level
    """
    logger = get_logger("errors")

    context_str = ""
    if context:
        context_str = " " + _truncate_dict(context, max_value_len=50)

    logger.log(
        level,
        "%s: %s%s",
        type(error).__name__,
        str(error),
        context_str,
        exc_info=True,
    )


def _truncate_dict(d: Dict[str, Any], max_value_len: int = 100) -> str:
    """
    Truncate dictionary values for logging.

    Args:
        d: Dictionary to truncate
        max_value_len: Maximum value length

    Returns:
        String representation
    """
    parts = []
    for k, v in d.items():
        v_str = str(v)
        if len(v_str) > max_value_len:
            v_str = v_str[:max_value_len] + "..."
        parts.append(f"{k}={v_str}")

    return ", ".join(parts)


# ===== Convenience Aliases =====


debug = get_logger("").debug
info = get_logger("").info
warning = get_logger("").warning
error = get_logger("").error
critical = get_logger("").critical
