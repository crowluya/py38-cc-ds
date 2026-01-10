"""
Tests for Streaming Output (T022)

Python 3.8.10 compatible
"""

import pytest
import sys
from typing import Any, Dict, List, Iterator
from unittest.mock import Mock, MagicMock, patch
from io import StringIO


class TestStreamPrinter:
    """Tests for StreamPrinter."""

    def test_print_chunk(self):
        """Test printing a single chunk."""
        from deep_code.cli.stream import StreamPrinter

        output = StringIO()
        printer = StreamPrinter(output=output)

        printer.print_chunk("Hello")

        assert output.getvalue() == "Hello"

    def test_print_multiple_chunks(self):
        """Test printing multiple chunks."""
        from deep_code.cli.stream import StreamPrinter

        output = StringIO()
        printer = StreamPrinter(output=output)

        printer.print_chunk("Hello")
        printer.print_chunk(" ")
        printer.print_chunk("World")

        assert output.getvalue() == "Hello World"

    def test_print_newline_on_finish(self):
        """Test newline is printed on finish."""
        from deep_code.cli.stream import StreamPrinter

        output = StringIO()
        printer = StreamPrinter(output=output)

        printer.print_chunk("Hello")
        printer.finish()

        assert output.getvalue() == "Hello\n"

    def test_flush_after_chunk(self):
        """Test output is flushed after each chunk."""
        from deep_code.cli.stream import StreamPrinter

        output = Mock()
        output.write = Mock()
        output.flush = Mock()

        printer = StreamPrinter(output=output)
        printer.print_chunk("test")

        output.flush.assert_called()


class TestStreamRenderer:
    """Tests for StreamRenderer with formatting."""

    def test_render_plain_text(self):
        """Test rendering plain text."""
        from deep_code.cli.stream import StreamRenderer

        output = StringIO()
        renderer = StreamRenderer(output=output, use_color=False)

        renderer.render_chunk("Hello World")

        assert "Hello World" in output.getvalue()

    def test_render_with_prefix(self):
        """Test rendering with prefix."""
        from deep_code.cli.stream import StreamRenderer

        output = StringIO()
        renderer = StreamRenderer(output=output, use_color=False, prefix="AI: ")

        renderer.start()
        renderer.render_chunk("Hello")
        renderer.finish()

        assert "AI: " in output.getvalue()

    def test_render_tool_start(self):
        """Test rendering tool start notification."""
        from deep_code.cli.stream import StreamRenderer

        output = StringIO()
        renderer = StreamRenderer(output=output, use_color=False)

        renderer.render_tool_start("Read", {"file_path": "/test.txt"})

        result = output.getvalue()
        assert "Read" in result

    def test_render_tool_end(self):
        """Test rendering tool end notification."""
        from deep_code.cli.stream import StreamRenderer
        from deep_code.core.tools.base import ToolResult

        output = StringIO()
        renderer = StreamRenderer(output=output, use_color=False)

        result = ToolResult.success_result("Read", "file content here")
        renderer.render_tool_end("Read", result)

        output_str = output.getvalue()
        assert "Read" in output_str

    def test_render_error(self):
        """Test rendering error message."""
        from deep_code.cli.stream import StreamRenderer

        output = StringIO()
        renderer = StreamRenderer(output=output, use_color=False)

        renderer.render_error("Something went wrong")

        assert "Something went wrong" in output.getvalue()


class TestStreamBuffer:
    """Tests for StreamBuffer."""

    def test_buffer_chunks(self):
        """Test buffering chunks."""
        from deep_code.cli.stream import StreamBuffer

        buffer = StreamBuffer()

        buffer.add("Hello")
        buffer.add(" ")
        buffer.add("World")

        assert buffer.get_content() == "Hello World"

    def test_buffer_clear(self):
        """Test clearing buffer."""
        from deep_code.cli.stream import StreamBuffer

        buffer = StreamBuffer()
        buffer.add("test")
        buffer.clear()

        assert buffer.get_content() == ""

    def test_buffer_is_empty(self):
        """Test is_empty check."""
        from deep_code.cli.stream import StreamBuffer

        buffer = StreamBuffer()
        assert buffer.is_empty

        buffer.add("x")
        assert not buffer.is_empty


class TestStreamCallbackAdapter:
    """Tests for StreamCallbackAdapter."""

    def test_adapter_calls_callback(self):
        """Test adapter calls the callback."""
        from deep_code.cli.stream import StreamCallbackAdapter

        received = []

        def callback(chunk):
            received.append(chunk)

        adapter = StreamCallbackAdapter(callback)
        adapter.on_chunk({"delta": "Hello"})
        adapter.on_chunk({"delta": " World"})

        assert len(received) == 2

    def test_adapter_extracts_delta(self):
        """Test adapter extracts delta from chunk."""
        from deep_code.cli.stream import StreamCallbackAdapter

        received = []

        def callback(text):
            received.append(text)

        adapter = StreamCallbackAdapter(callback, extract_delta=True)
        adapter.on_chunk({"delta": "Hello"})

        assert received == ["Hello"]

    def test_adapter_handles_none_callback(self):
        """Test adapter handles None callback gracefully."""
        from deep_code.cli.stream import StreamCallbackAdapter

        adapter = StreamCallbackAdapter(None)
        # Should not raise
        adapter.on_chunk({"delta": "test"})


class TestStreamIntegration:
    """Integration tests for streaming."""

    def test_stream_to_renderer(self):
        """Test streaming chunks to renderer."""
        from deep_code.cli.stream import StreamRenderer, stream_to_renderer

        output = StringIO()
        renderer = StreamRenderer(output=output, use_color=False)

        chunks = [
            {"delta": "Hello"},
            {"delta": " "},
            {"delta": "World"},
        ]

        stream_to_renderer(iter(chunks), renderer)

        assert "Hello World" in output.getvalue()

    def test_create_stream_handler(self):
        """Test creating stream handler for agent loop."""
        from deep_code.cli.stream import create_stream_handler

        output = StringIO()
        handler = create_stream_handler(output=output, use_color=False)

        # Handler should have on_chunk method
        assert hasattr(handler, "on_chunk")
        assert callable(handler.on_chunk)

        handler.on_chunk({"delta": "test"})
        assert "test" in output.getvalue()


class TestStreamProgress:
    """Tests for progress indicators."""

    def test_spinner_start_stop(self):
        """Test spinner start and stop."""
        from deep_code.cli.stream import Spinner

        output = StringIO()
        spinner = Spinner(output=output, message="Loading")

        spinner.start()
        spinner.stop()

        # Should not raise

    def test_progress_bar_update(self):
        """Test progress bar update."""
        from deep_code.cli.stream import ProgressBar

        output = StringIO()
        bar = ProgressBar(output=output, total=100)

        bar.update(50)

        result = output.getvalue()
        assert "50" in result or "%" in result
