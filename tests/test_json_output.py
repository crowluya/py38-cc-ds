"""
JSON output format tests (T091)

TDD: Tests for --json and --json-stream output formats
Python 3.8.10 compatible
"""

import json
from datetime import datetime
from typing import Any, List
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from deep_code.cli.main import cli
from deep_code.core.agent import ConversationTurn, ToolCall, ToolType


# ===== Test Fixtures =====


class FakeLLMClient:
    """Fake LLM client for testing."""

    def __init__(
        self,
        response: str = "Test response",
        finish_reason: str = "stop",
        tool_calls: Any = None,
    ):
        self._response = response
        self._finish_reason = finish_reason
        self._tool_calls = tool_calls
        self.last_messages = None

    def chat_completion(self, messages: Any, **kwargs: Any) -> Any:
        """Fake chat completion."""
        self.last_messages = messages
        response = Mock()
        response.content = self._response
        response.finish_reason = self._finish_reason
        response.tool_calls = self._tool_calls
        return response

    def chat_completion_stream(self, messages: Any, **kwargs: Any) -> List[Any]:
        """Fake streaming completion."""
        self.last_messages = messages

        # Yield multiple chunks
        chunks = []
        for word in self._response.split():
            chunk = Mock()
            chunk.content = word + " "
            chunks.append(chunk)

        return chunks

    def get_model(self) -> str:
        """Get model name."""
        return "fake-model"

    def validate_config(self) -> bool:
        """Validate config."""
        return True


def create_sample_tool_calls() -> List[ToolCall]:
    """Create sample tool calls for testing."""
    return [
        ToolCall(
            tool_type=ToolType.SHELL,
            command="ls -la",
            arguments={},
            call_id="call_123",
        ),
        ToolCall(
            tool_type=ToolType.READ_FILE,
            command="test.txt",
            arguments={},
            call_id="call_456",
        ),
    ]


# ===== Tests for --json flag =====


def test_json_output_with_basic_response():
    """Test --json flag outputs valid JSON with all required fields."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Hello World")

        result = runner.invoke(cli, ["chat", "-p", "Say hello", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.output)

        # Verify required fields
        assert "content" in output_data
        assert "finish_reason" in output_data
        assert "tool_calls" in output_data
        assert "timestamp" in output_data

        # Verify content
        assert output_data["content"] == "Hello World"
        assert output_data["finish_reason"] == "stop"

        # Verify tool_calls is null/empty for basic response
        assert output_data["tool_calls"] is None or output_data["tool_calls"] == []

        # Verify timestamp is valid ISO format (Python 3.8 compatible)
        # Python 3.8's fromisoformat doesn't handle 'Z' suffix, so strip it if present
        timestamp_str = output_data["timestamp"]
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1]
        datetime.fromisoformat(timestamp_str)


def test_json_output_with_finish_reasons():
    """Test --json flag captures different finish reasons."""
    runner = CliRunner()

    for reason in ["stop", "length", "content_filter"]:
        with patch("deep_code.cli.main.create_llm_client") as mock_factory:
            mock_factory.return_value = FakeLLMClient(
                response="Response",
                finish_reason=reason,
            )

            result = runner.invoke(cli, ["chat", "-p", "Test", "--json"])

            assert result.exit_code == 0

            output_data = json.loads(result.output)
            assert output_data["finish_reason"] == reason


def test_json_output_with_tool_calls():
    """Test --json flag includes tool_calls in response."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        tool_calls = create_sample_tool_calls()
        mock_factory.return_value = FakeLLMClient(
            response="I'll run those commands",
            tool_calls=tool_calls,
        )

        result = runner.invoke(cli, ["chat", "-p", "Run ls", "--json"])

        assert result.exit_code == 0

        output_data = json.loads(result.output)

        # Verify tool_calls field exists and has correct structure
        assert "tool_calls" in output_data
        assert output_data["tool_calls"] is not None
        assert len(output_data["tool_calls"]) == 2

        # Verify first tool call
        first_tool = output_data["tool_calls"][0]
        assert "tool_type" in first_tool
        assert "command" in first_tool
        assert "call_id" in first_tool
        assert first_tool["tool_type"] == "shell"
        assert first_tool["command"] == "ls -la"


def test_json_output_with_multiline_content():
    """Test --json flag handles multiline content correctly."""
    runner = CliRunner()

    multiline_response = """Line 1
Line 2
Line 3"""

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient(multiline_response)

        result = runner.invoke(cli, ["chat", "-p", "Get multiline", "--json"])

        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["content"] == multiline_response
        assert "\n" in output_data["content"]


def test_json_output_with_special_characters():
    """Test --json flag handles special characters correctly."""
    runner = CliRunner()

    special_content = 'Special chars: "quotes", {braces}, [brackets], \t\n\n'

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient(special_content)

        result = runner.invoke(cli, ["chat", "-p", "Special chars", "--json"])

        assert result.exit_code == 0

        # Should be valid JSON (no parse errors)
        output_data = json.loads(result.output)
        assert output_data["content"] == special_content


def test_json_output_with_empty_content():
    """Test --json flag handles empty response."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("")

        result = runner.invoke(cli, ["chat", "-p", "Empty", "--json"])

        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert "content" in output_data
        assert output_data["content"] == ""


def test_json_output_error_handling():
    """Test --json flag handles errors gracefully."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_client = Mock()
        mock_client.chat_completion.side_effect = Exception("LLM failed")
        mock_factory.return_value = mock_client

        result = runner.invoke(cli, ["chat", "-p", "Test", "--json"])

        # Should still output JSON error
        assert result.exit_code != 0
        # Try to parse as JSON
        try:
            output_data = json.loads(result.output)
            assert "error" in output_data or "content" in output_data
        except json.JSONDecodeError:
            # If not JSON, should have error message
            assert "error" in result.output.lower()


# ===== Tests for --json-stream flag =====


def test_json_stream_outputs_multiple_json_objects():
    """Test --json-stream outputs multiple JSON objects."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Hello World")

        result = runner.invoke(cli, ["chat", "-p", "Say hello", "--json-stream"])

        assert result.exit_code == 0

        # Stream output should have multiple JSON objects
        lines = result.output.strip().split("\n")

        # Each line should be valid JSON
        json_objects = []
        for line in lines:
            if line.strip():  # Skip empty lines
                obj = json.loads(line)
                json_objects.append(obj)

        # Should have at least one chunk
        assert len(json_objects) > 0

        # Verify each chunk has required fields
        for obj in json_objects:
            assert "content" in obj or "done" in obj
            if "content" in obj:
                assert isinstance(obj["content"], str)


def test_json_stream_final_chunk_has_done_flag():
    """Test --json-stream final chunk has done=True."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Final response")

        result = runner.invoke(cli, ["chat", "-p", "Test", "--json-stream"])

        assert result.exit_code == 0

        lines = result.output.strip().split("\n")
        last_line = lines[-1]

        final_obj = json.loads(last_line)
        assert "done" in final_obj
        assert final_obj["done"] is True


def test_json_stream_includes_finish_reason_in_final_chunk():
    """Test --json-stream includes finish_reason in final chunk."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient(
            response="Response",
            finish_reason="stop",
        )

        result = runner.invoke(cli, ["chat", "-p", "Test", "--json-stream"])

        assert result.exit_code == 0

        lines = result.output.strip().split("\n")
        last_line = lines[-1]

        final_obj = json.loads(last_line)
        assert "finish_reason" in final_obj
        assert final_obj["finish_reason"] == "stop"


def test_json_stream_with_tool_calls():
    """Test --json-stream handles tool calls in final chunk."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        tool_calls = create_sample_tool_calls()
        mock_factory.return_value = FakeLLMClient(
            response="Running tools",
            tool_calls=tool_calls,
        )

        result = runner.invoke(cli, ["chat", "-p", "Run tools", "--json-stream"])

        assert result.exit_code == 0

        lines = result.output.strip().split("\n")
        last_line = lines[-1]

        final_obj = json.loads(last_line)
        # MVP: Streaming doesn't support tool calls, but should have done flag
        assert "done" in final_obj
        assert final_obj["done"] is True


# ===== Tests for JSON schema validation =====


def test_json_schema_all_required_fields_present():
    """Test JSON output contains all required fields."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Complete response")

        result = runner.invoke(cli, ["chat", "-p", "Test", "--json"])

        assert result.exit_code == 0

        output_data = json.loads(result.output)

        # All required fields per T091 spec
        required_fields = ["content", "finish_reason", "tool_calls", "timestamp"]
        for field in required_fields:
            assert field in output_data, f"Missing required field: {field}"


def test_json_field_types():
    """Test JSON output field types are correct."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Typed response")

        result = runner.invoke(cli, ["chat", "-p", "Test", "--json"])

        assert result.exit_code == 0

        output_data = json.loads(result.output)

        # Type checks
        assert isinstance(output_data["content"], str)
        assert isinstance(output_data["finish_reason"], str)
        assert isinstance(output_data["timestamp"], str)

        # tool_calls can be None or list
        if output_data["tool_calls"] is not None:
            assert isinstance(output_data["tool_calls"], list)


# ===== Tests for integration with existing flags =====


def test_json_with_model_override():
    """Test --json flag works with -m/--model flag."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Model response")

        result = runner.invoke(
            cli,
            ["chat", "-p", "Test", "-m", "custom-model", "--json"],
        )

        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert "content" in output_data


def test_json_with_stdin_input():
    """Test --json flag works with stdin input."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Stdin processed")

        result = runner.invoke(cli, ["chat", "-p", "--json"], input="From stdin")

        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["content"] == "Stdin processed"


# ===== Tests for edge cases =====


def test_json_output_unicode_content():
    """Test --json flag handles unicode characters."""
    runner = CliRunner()

    unicode_content = "Unicode: 你好世界 🌍 Ñoño"

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient(unicode_content)

        result = runner.invoke(cli, ["chat", "-p", "Unicode", "--json"])

        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["content"] == unicode_content


def test_json_output_very_long_content():
    """Test --json flag handles very long responses."""
    runner = CliRunner()

    long_content = "Word " * 10000  # Large response

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient(long_content)

        result = runner.invoke(cli, ["chat", "-p", "Long", "--json"])

        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert len(output_data["content"]) == len(long_content)


def test_json_stream_empty_chunks():
    """Test --json-stream handles empty chunks gracefully."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("")

        result = runner.invoke(cli, ["chat", "-p", "Empty", "--json-stream"])

        assert result.exit_code == 0

        # Should still have valid output
        lines = result.output.strip().split("\n")
        if lines:
            # At minimum should have final done message
            last_obj = json.loads(lines[-1])
            assert "done" in last_obj


# ===== Tests for CLI output format option =====


def test_print_command_with_json_format():
    """Test 'print' command with --output-format json."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Print command response")

        result = runner.invoke(
            cli,
            ["print", "Test prompt", "-o", "json"],
        )

        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert "content" in output_data
        assert output_data["content"] == "Print command response"


def test_print_command_with_stream_json_format():
    """Test 'print' command with --output-format stream-json."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Stream response")

        result = runner.invoke(
            cli,
            ["print", "Test prompt", "-o", "stream-json"],
        )

        assert result.exit_code == 0

        # Should output multiple JSON lines
        lines = result.output.strip().split("\n")
        assert len(lines) > 0

        # Each line should be valid JSON
        for line in lines:
            if line.strip():
                json.loads(line)


# ===== Helper function tests =====


def test_json_formatter_helper():
    """Test JSON formatter helper function directly."""
    from deep_code.cli.output import format_json_output, format_json_stream_chunk

    # Test basic JSON formatting with individual parameters
    json_str = format_json_output(
        content="Test content",
        finish_reason="stop",
        tool_calls=None,
    )
    data = json.loads(json_str)

    assert data["content"] == "Test content"
    assert data["finish_reason"] == "stop"
    assert "timestamp" in data


def test_json_stream_chunk_formatter():
    """Test JSON stream chunk formatter."""
    from deep_code.cli.output import format_json_stream_chunk

    # Test content chunk
    chunk = format_json_stream_chunk(content="Hello", done=False)
    data = json.loads(chunk)

    assert data["content"] == "Hello"
    assert data["done"] is False

    # Test final chunk
    final = format_json_stream_chunk(done=True, finish_reason="stop", tool_calls=None)
    data = json.loads(final)

    assert data["done"] is True
    assert data["finish_reason"] == "stop"
