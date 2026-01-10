"""
Tests for Logging System (T023)

Python 3.8.10 compatible
"""

import pytest
import logging
import os
import tempfile
from typing import Any, Dict, List
from io import StringIO


class TestLoggerSetup:
    """Tests for logger setup."""

    def test_get_logger(self):
        """Test getting a logger."""
        from deep_code.core.logging import get_logger

        logger = get_logger("test")

        assert logger is not None
        assert logger.name == "deep_code.test"

    def test_get_logger_with_full_name(self):
        """Test getting logger with full name."""
        from deep_code.core.logging import get_logger

        logger = get_logger("deep_code.core.agent")

        assert logger.name == "deep_code.core.agent"

    def test_setup_logging_default(self):
        """Test default logging setup."""
        from deep_code.core.logging import setup_logging

        setup_logging()

        root_logger = logging.getLogger("deep_code")
        assert root_logger.level == logging.INFO

    def test_setup_logging_debug(self):
        """Test debug level logging setup."""
        from deep_code.core.logging import setup_logging

        setup_logging(level="DEBUG")

        root_logger = logging.getLogger("deep_code")
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_with_file(self):
        """Test logging to file."""
        from deep_code.core.logging import setup_logging

        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_file = f.name

        try:
            setup_logging(log_file=log_file)

            logger = logging.getLogger("deep_code.test")
            logger.info("Test message")

            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

            assert "Test message" in content
        finally:
            os.unlink(log_file)


class TestLogFormatter:
    """Tests for log formatter."""

    def test_format_basic_message(self):
        """Test basic message formatting."""
        from deep_code.core.logging import DeepCodeFormatter

        formatter = DeepCodeFormatter()
        record = logging.LogRecord(
            name="deep_code.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert "INFO" in formatted
        assert "Test message" in formatted

    def test_format_with_exception(self):
        """Test formatting with exception."""
        from deep_code.core.logging import DeepCodeFormatter

        formatter = DeepCodeFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="deep_code.test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        formatted = formatter.format(record)

        assert "ERROR" in formatted
        assert "ValueError" in formatted
        assert "Test error" in formatted

    def test_format_with_context(self):
        """Test formatting with extra context."""
        from deep_code.core.logging import DeepCodeFormatter

        formatter = DeepCodeFormatter(include_context=True)
        record = logging.LogRecord(
            name="deep_code.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.tool_name = "Read"

        formatted = formatter.format(record)

        assert "Test message" in formatted


class TestLogFilter:
    """Tests for log filters."""

    def test_level_filter(self):
        """Test level-based filtering."""
        from deep_code.core.logging import LevelFilter

        filter = LevelFilter(min_level=logging.WARNING)

        info_record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="", args=(), exc_info=None
        )
        warning_record = logging.LogRecord(
            name="test", level=logging.WARNING,
            pathname="", lineno=0, msg="", args=(), exc_info=None
        )

        assert filter.filter(info_record) is False
        assert filter.filter(warning_record) is True

    def test_module_filter(self):
        """Test module-based filtering."""
        from deep_code.core.logging import ModuleFilter

        filter = ModuleFilter(allowed_modules=["deep_code.core"])

        core_record = logging.LogRecord(
            name="deep_code.core.agent", level=logging.INFO,
            pathname="", lineno=0, msg="", args=(), exc_info=None
        )
        cli_record = logging.LogRecord(
            name="deep_code.cli.main", level=logging.INFO,
            pathname="", lineno=0, msg="", args=(), exc_info=None
        )

        assert filter.filter(core_record) is True
        assert filter.filter(cli_record) is False


class TestLogContext:
    """Tests for logging context."""

    def test_log_context_manager(self):
        """Test logging context manager."""
        from deep_code.core.logging import log_context, get_logger

        logger = get_logger("test")

        with log_context(tool="Read", file="/test.txt"):
            # Context should be available
            pass

    def test_log_with_context(self):
        """Test logging with context data."""
        from deep_code.core.logging import get_logger

        logger = get_logger("test")

        # Should not raise
        logger.info("Message", extra={"tool": "Read"})


class TestLogHelpers:
    """Tests for logging helper functions."""

    def test_log_tool_call(self):
        """Test tool call logging helper."""
        from deep_code.core.logging import log_tool_call

        # Should not raise
        log_tool_call("Read", {"file_path": "/test.txt"})

    def test_log_tool_result(self):
        """Test tool result logging helper."""
        from deep_code.core.logging import log_tool_result
        from deep_code.core.tools.base import ToolResult

        result = ToolResult.success_result("Read", "content")

        # Should not raise
        log_tool_result("Read", result)

    def test_log_llm_call(self):
        """Test LLM call logging helper."""
        from deep_code.core.logging import log_llm_call

        # Should not raise
        log_llm_call(
            model="deepseek-r1",
            messages=[{"role": "user", "content": "Hello"}],
            tokens=100,
        )

    def test_log_error(self):
        """Test error logging helper."""
        from deep_code.core.logging import log_error

        try:
            raise ValueError("Test error")
        except ValueError as e:
            # Should not raise
            log_error(e, context={"operation": "test"})


class TestLogRotation:
    """Tests for log rotation."""

    def test_rotating_file_handler(self):
        """Test rotating file handler setup."""
        from deep_code.core.logging import setup_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")

            setup_logging(
                log_file=log_file,
                max_bytes=1024,
                backup_count=3,
            )

            logger = logging.getLogger("deep_code.test")

            # Write enough to trigger rotation
            for i in range(100):
                logger.info("Test message %d with padding text to fill space", i)

            # Check that log file exists
            assert os.path.exists(log_file)


class TestLogPerformance:
    """Tests for logging performance."""

    def test_lazy_formatting(self):
        """Test that log messages use lazy formatting."""
        from deep_code.core.logging import get_logger

        logger = get_logger("test")
        logger.setLevel(logging.WARNING)

        # This should not evaluate the expensive format
        call_count = 0

        class ExpensiveObject:
            def __str__(self):
                nonlocal call_count
                call_count += 1
                return "expensive"

        obj = ExpensiveObject()
        logger.debug("Message: %s", obj)

        # __str__ should not be called for debug when level is WARNING
        assert call_count == 0
