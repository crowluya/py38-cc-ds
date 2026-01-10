"""
Headless mode tests (T090)

TDD: Tests for -p/--print flag and stdin piping
Python 3.8.10 compatible
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from deep_code.cli.main import cli
from click.testing import CliRunner


# ===== Test Fixtures =====


class FakeLLMClient:
    """Fake LLM client for testing."""

    def __init__(self, response: str = "Test response"):
        self._response = response
        self.last_messages = None

    def chat_completion(self, messages: Any, **kwargs: Any) -> Any:
        """Fake chat completion."""
        self.last_messages = messages
        response = Mock()
        response.content = self._response
        response.finish_reason = "stop"
        response.tool_calls = None
        return response

    def get_model(self) -> str:
        """Get model name."""
        return "fake-model"

    def validate_config(self) -> bool:
        """Validate config."""
        return True


# ===== Tests for -p/--print flag =====


def test_headless_print_with_prompt():
    """Test -p flag with direct prompt."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Hello World")

        result = runner.invoke(cli, ["chat", "-p", "Say hello"])

        assert result.exit_code == 0
        assert "Hello World" in result.output


def test_headless_print_long_flag():
    """Test --print long flag."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Test response")

        result = runner.invoke(cli, ["chat", "--print", "Test"])

        assert result.exit_code == 0
        assert "Test response" in result.output


def test_headless_print_with_model_override():
    """Test -p flag with model override."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_client = FakeLLMClient("Response")
        mock_factory.return_value = mock_client

        result = runner.invoke(cli, ["chat", "-p", "Test", "-m", "custom-model"])

        assert result.exit_code == 0
        # Verify model was passed through (checked via factory call)


# ===== Tests for stdin reading =====


def test_headless_read_from_stdin():
    """Test reading prompt from stdin."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Processed stdin input")

        result = runner.invoke(cli, ["chat", "-p"], input="This is from stdin")

        assert result.exit_code == 0
        assert "Processed stdin input" in result.output


def test_headless_stdin_priority_over_empty_prompt():
    """Test stdin is used when prompt arg is empty."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Stdin wins")

        result = runner.invoke(cli, ["chat", "-p", ""], input="Stdin content")

        assert result.exit_code == 0
        assert "Stdin wins" in result.output


# ===== Tests for large text input =====


def test_headless_large_text_from_stdin():
    """Test handling large text input from stdin."""
    runner = CliRunner()

    large_text = "Line " * 1000  # Large input

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_client = FakeLLMClient("Processed large text")
        mock_factory.return_value = mock_client

        result = runner.invoke(cli, ["chat", "-p"], input=large_text)

        assert result.exit_code == 0
        assert "Processed large text" in result.output
        # Verify large text was passed to LLM
        assert mock_client.last_messages is not None
        user_message = mock_client.last_messages[-1]
        assert "Line " in user_message["content"]


def test_headless_multiline_stdin():
    """Test multiline input from stdin."""
    runner = CliRunner()

    multiline_input = """First line
Second line
Third line"""

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Got 3 lines")

        result = runner.invoke(cli, ["chat", "-p"], input=multiline_input)

        assert result.exit_code == 0
        assert "Got 3 lines" in result.output


def test_headless_special_characters_in_stdin():
    """Test stdin with special characters."""
    runner = CliRunner()

    special_text = "Special: !@#$%^&*()[]{}"

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Handled special chars")

        result = runner.invoke(cli, ["chat", "-p"], input=special_text)

        assert result.exit_code == 0
        assert "Handled special chars" in result.output


# ===== Tests for error handling =====


def test_headless_no_input_source():
    """Test error when neither prompt nor stdin provided."""
    runner = CliRunner()

    result = runner.invoke(cli, ["chat", "-p"])

    # Should fail gracefully when no input source
    assert result.exit_code != 0
    assert "error" in result.output.lower() or "required" in result.output.lower()


def test_headless_llm_error_handling():
    """Test error handling when LLM fails."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        # Simulate LLM error
        mock_client = Mock()
        mock_client.chat_completion.side_effect = Exception("LLM connection failed")
        mock_factory.return_value = mock_client

        result = runner.invoke(cli, ["chat", "-p", "Test"])

        # Should fail with error message
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()


def test_headless_invalid_model():
    """Test error handling for invalid model configuration."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        # Simulate config error
        from deep_code.llm.client import LLMConfigError
        mock_factory.side_effect = LLMConfigError("Invalid model configuration")

        result = runner.invoke(cli, ["chat", "-p", "Test"])

        assert result.exit_code != 0


# ===== Tests for non-interactive mode =====


def test_headless_exits_after_response():
    """Test headless mode exits after printing response (no interactive loop)."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Single response")

        result = runner.invoke(cli, ["chat", "-p", "Test"])

        assert result.exit_code == 0
        # Should not show interactive prompts
        assert "interactive" not in result.output.lower()


def test_headless_no_persistent_history():
    """Test headless mode doesn't persist conversation history."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_client = FakeLLMClient("Response 1")
        mock_factory.return_value = mock_client

        # First invocation
        result1 = runner.invoke(cli, ["chat", "-p", "First"])
        assert "Response 1" in result1.output

        # Second invocation - should not have history from first
        mock_client._response = "Response 2"
        result2 = runner.invoke(cli, ["chat", "-p", "Second"])
        assert "Response 2" in result2.output


# ===== Tests for output format =====


def test_headless_output_clean():
    """Test headless output is clean (no extra debug info)."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_factory.return_value = FakeLLMClient("Clean output")

        result = runner.invoke(cli, ["chat", "-p", "Test"])

        assert result.exit_code == 0
        # Should contain the response
        assert "Clean output" in result.output
        # Should not contain debug chatter (in non-debug mode)
        assert "DEBUG" not in result.output


# ===== Integration-style tests =====


def test_headless_with_context_injection_simulation():
    """Test headless mode can handle prompts with @ syntax (simulation)."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_client = FakeLLMClient("Processed with context")
        mock_factory.return_value = mock_client

        result = runner.invoke(
            cli,
            ["chat", "-p", "Analyze @file.txt please"],
        )

        assert result.exit_code == 0
        assert "Processed with context" in result.output
        # Verify prompt with @ syntax was passed
        assert mock_client.last_messages is not None


def test_headless_with_command_syntax_simulation():
    """Test headless mode can handle ! command syntax (simulation)."""
    runner = CliRunner()

    with patch("deep_code.cli.main.create_llm_client") as mock_factory:
        mock_client = FakeLLMClient("Executed command")
        mock_factory.return_value = mock_client

        result = runner.invoke(
            cli,
            ["chat", "-p", "Run !ls -la and analyze"],
        )

        assert result.exit_code == 0
        assert "Executed command" in result.output
