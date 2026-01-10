"""
Tests for Interactive REPL (T025)

Python 3.8.10 compatible
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import Mock, MagicMock, patch
from io import StringIO


class TestREPLSession:
    """Tests for REPL session."""

    def test_create_session(self):
        """Test creating a REPL session."""
        from deep_code.cli.repl import REPLSession, REPLConfig

        mock_agent = Mock()
        config = REPLConfig(agent=mock_agent)
        session = REPLSession(config)

        assert session is not None

    def test_session_process_input(self):
        """Test processing user input."""
        from deep_code.cli.repl import REPLSession, REPLConfig

        mock_agent = Mock()
        mock_agent.run_turn.return_value = Mock(content="Response", has_tool_calls=False)

        config = REPLConfig(agent=mock_agent)
        session = REPLSession(config)

        result = session.process_input("Hello")

        assert result is not None
        mock_agent.run_turn.assert_called_once_with("Hello")

    def test_session_exit_commands(self):
        """Test exit commands."""
        from deep_code.cli.repl import REPLSession, REPLConfig

        mock_agent = Mock()
        config = REPLConfig(agent=mock_agent)
        session = REPLSession(config)

        assert session.is_exit_command("exit")
        assert session.is_exit_command("quit")
        assert session.is_exit_command("/exit")
        assert not session.is_exit_command("hello")

    def test_session_slash_commands(self):
        """Test slash command detection."""
        from deep_code.cli.repl import REPLSession, REPLConfig

        mock_agent = Mock()
        config = REPLConfig(agent=mock_agent)
        session = REPLSession(config)

        assert session.is_slash_command("/help")
        assert session.is_slash_command("/clear")
        assert not session.is_slash_command("hello")

    def test_session_handle_help(self):
        """Test /help command."""
        from deep_code.cli.repl import REPLSession, REPLConfig

        mock_agent = Mock()
        output = StringIO()
        config = REPLConfig(agent=mock_agent, output=output)
        session = REPLSession(config)

        session.handle_slash_command("/help")

        result = output.getvalue()
        assert "help" in result.lower() or "command" in result.lower()

    def test_session_handle_clear(self):
        """Test /clear command."""
        from deep_code.cli.repl import REPLSession, REPLConfig

        mock_agent = Mock()
        config = REPLConfig(agent=mock_agent)
        session = REPLSession(config)

        session.handle_slash_command("/clear")

        mock_agent.reset.assert_called_once()


class TestREPLInput:
    """Tests for REPL input handling."""

    def test_multiline_input(self):
        """Test multiline input detection."""
        from deep_code.cli.repl import is_multiline_input

        assert is_multiline_input("line1\nline2")
        assert not is_multiline_input("single line")

    def test_input_continuation(self):
        """Test input continuation detection."""
        from deep_code.cli.repl import needs_continuation

        assert needs_continuation("def foo():")
        assert needs_continuation("if True:")
        assert needs_continuation("line \\")
        assert not needs_continuation("complete line")

    def test_strip_input(self):
        """Test input stripping."""
        from deep_code.cli.repl import strip_input

        assert strip_input("  hello  ") == "hello"
        assert strip_input("hello\n") == "hello"


class TestREPLHistory:
    """Tests for REPL history."""

    def test_history_add(self):
        """Test adding to history."""
        from deep_code.cli.repl import REPLHistory

        history = REPLHistory()
        history.add("command 1")
        history.add("command 2")

        assert len(history) == 2

    def test_history_get(self):
        """Test getting history items."""
        from deep_code.cli.repl import REPLHistory

        history = REPLHistory()
        history.add("command 1")
        history.add("command 2")

        assert history.get(0) == "command 1"
        assert history.get(1) == "command 2"

    def test_history_navigation(self):
        """Test history navigation."""
        from deep_code.cli.repl import REPLHistory

        history = REPLHistory()
        history.add("cmd1")
        history.add("cmd2")
        history.add("cmd3")

        assert history.previous() == "cmd3"
        assert history.previous() == "cmd2"
        assert history.next() == "cmd3"

    def test_history_save_load(self, tmp_path):
        """Test history save and load."""
        from deep_code.cli.repl import REPLHistory

        history_file = tmp_path / "history.txt"

        history1 = REPLHistory(str(history_file))
        history1.add("cmd1")
        history1.add("cmd2")
        history1.save()

        history2 = REPLHistory(str(history_file))
        history2.load()

        assert len(history2) == 2

    def test_history_max_size(self):
        """Test history max size limit."""
        from deep_code.cli.repl import REPLHistory

        history = REPLHistory(max_size=3)
        history.add("cmd1")
        history.add("cmd2")
        history.add("cmd3")
        history.add("cmd4")

        assert len(history) == 3
        assert history.get(0) == "cmd2"  # cmd1 should be removed


class TestREPLPrompt:
    """Tests for REPL prompt."""

    def test_default_prompt(self):
        """Test default prompt."""
        from deep_code.cli.repl import get_prompt

        prompt = get_prompt()

        assert ">" in prompt or ":" in prompt

    def test_custom_prompt(self):
        """Test custom prompt."""
        from deep_code.cli.repl import get_prompt

        prompt = get_prompt(prefix="AI")

        assert "AI" in prompt

    def test_continuation_prompt(self):
        """Test continuation prompt."""
        from deep_code.cli.repl import get_continuation_prompt

        prompt = get_continuation_prompt()

        assert "..." in prompt or ">" in prompt


class TestREPLCommands:
    """Tests for built-in REPL commands."""

    def test_help_command(self):
        """Test help command output."""
        from deep_code.cli.repl import get_help_text

        help_text = get_help_text()

        assert "/help" in help_text
        assert "/exit" in help_text or "/quit" in help_text

    def test_parse_slash_command(self):
        """Test parsing slash commands."""
        from deep_code.cli.repl import parse_slash_command

        cmd, args = parse_slash_command("/help")
        assert cmd == "help"
        assert args == []

        cmd, args = parse_slash_command("/read file.txt")
        assert cmd == "read"
        assert args == ["file.txt"]

    def test_available_commands(self):
        """Test getting available commands."""
        from deep_code.cli.repl import get_available_commands

        commands = get_available_commands()

        assert "help" in commands
        assert "exit" in commands
        assert "clear" in commands


class TestREPLConfig:
    """Tests for REPL configuration."""

    def test_default_config(self):
        """Test default configuration."""
        from deep_code.cli.repl import REPLConfig

        mock_agent = Mock()
        config = REPLConfig(agent=mock_agent)

        assert config.prompt == "> "
        assert config.history_file is None
        assert config.max_history == 1000

    def test_custom_config(self):
        """Test custom configuration."""
        from deep_code.cli.repl import REPLConfig

        mock_agent = Mock()
        config = REPLConfig(
            agent=mock_agent,
            prompt="AI> ",
            max_history=500,
        )

        assert config.prompt == "AI> "
        assert config.max_history == 500


class TestREPLIntegration:
    """Integration tests for REPL."""

    def test_full_conversation(self):
        """Test a full conversation flow."""
        from deep_code.cli.repl import REPLSession, REPLConfig

        mock_agent = Mock()
        mock_agent.run_turn.side_effect = [
            Mock(content="Hello!", has_tool_calls=False),
            Mock(content="I can help with that.", has_tool_calls=False),
        ]

        output = StringIO()
        config = REPLConfig(agent=mock_agent, output=output)
        session = REPLSession(config)

        session.process_input("Hi")
        session.process_input("Help me")

        assert mock_agent.run_turn.call_count == 2

    def test_error_handling(self):
        """Test error handling in REPL."""
        from deep_code.cli.repl import REPLSession, REPLConfig

        mock_agent = Mock()
        mock_agent.run_turn.side_effect = Exception("Test error")

        output = StringIO()
        config = REPLConfig(agent=mock_agent, output=output)
        session = REPLSession(config)

        # Should not raise
        session.process_input("Hello")

        result = output.getvalue()
        assert "error" in result.lower()
