"""
Interactive REPL (T025)

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Provides:
- Interactive Read-Eval-Print Loop
- Command history with navigation
- Slash commands (/help, /clear, /exit)
- Multiline input support
- Customizable prompts
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TextIO, Tuple


@dataclass
class REPLConfig:
    """Configuration for REPL session."""
    agent: Any
    prompt: str = "> "
    continuation_prompt: str = "... "
    history_file: Optional[str] = None
    max_history: int = 1000
    output: Optional[TextIO] = None
    use_color: bool = True
    show_welcome: bool = True


class REPLHistory:
    """Command history with navigation."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        max_size: int = 1000,
    ) -> None:
        """
        Initialize history.

        Args:
            file_path: Optional file to persist history
            max_size: Maximum history size
        """
        self._history: List[str] = []
        self._file_path = file_path
        self._max_size = max_size
        self._position = 0

    def add(self, command: str) -> None:
        """
        Add command to history.

        Args:
            command: Command to add
        """
        if command.strip():
            self._history.append(command)
            # Trim if exceeds max size
            if len(self._history) > self._max_size:
                self._history = self._history[-self._max_size:]
            self._position = len(self._history)

    def get(self, index: int) -> Optional[str]:
        """
        Get command at index.

        Args:
            index: History index

        Returns:
            Command or None
        """
        if 0 <= index < len(self._history):
            return self._history[index]
        return None

    def previous(self) -> Optional[str]:
        """
        Get previous command.

        Returns:
            Previous command or None
        """
        if self._position > 0:
            self._position -= 1
            return self._history[self._position]
        return None

    def next(self) -> Optional[str]:
        """
        Get next command.

        Returns:
            Next command or None
        """
        if self._position < len(self._history) - 1:
            self._position += 1
            return self._history[self._position]
        return None

    def reset_position(self) -> None:
        """Reset navigation position to end."""
        self._position = len(self._history)

    def save(self) -> None:
        """Save history to file."""
        if self._file_path:
            try:
                with open(self._file_path, "w", encoding="utf-8") as f:
                    for cmd in self._history:
                        f.write(cmd + "\n")
            except Exception:
                pass  # Silently fail

    def load(self) -> None:
        """Load history from file."""
        if self._file_path and os.path.exists(self._file_path):
            try:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    self._history = [line.rstrip("\n") for line in f]
                    self._position = len(self._history)
            except Exception:
                pass  # Silently fail

    def __len__(self) -> int:
        """Return history length."""
        return len(self._history)


class REPLSession:
    """Interactive REPL session."""

    EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", "q"}
    SLASH_COMMANDS = {
        "help": "Show help message",
        "clear": "Clear conversation history",
        "exit": "Exit the REPL",
        "quit": "Exit the REPL",
        "history": "Show command history",
        "reset": "Reset the session",
    }

    def __init__(self, config: REPLConfig) -> None:
        """
        Initialize REPL session.

        Args:
            config: REPL configuration
        """
        self._config = config
        self._agent = config.agent
        self._output = config.output or sys.stdout
        self._history = REPLHistory(
            file_path=config.history_file,
            max_size=config.max_history,
        )
        self._running = False

        # Load history if file specified
        if config.history_file:
            self._history.load()

    def process_input(self, user_input: str) -> Optional[Any]:
        """
        Process user input.

        Args:
            user_input: User input string

        Returns:
            Response or None
        """
        user_input = strip_input(user_input)

        if not user_input:
            return None

        # Add to history
        self._history.add(user_input)

        # Check for exit
        if self.is_exit_command(user_input):
            self._running = False
            return None

        # Check for slash command
        if self.is_slash_command(user_input):
            return self.handle_slash_command(user_input)

        # Process with agent
        try:
            result = self._agent.run_turn(user_input)
            self._print_response(result)
            return result
        except Exception as e:
            self._print_error(str(e))
            return None

    def is_exit_command(self, text: str) -> bool:
        """Check if text is an exit command."""
        return text.lower().strip() in self.EXIT_COMMANDS

    def is_slash_command(self, text: str) -> bool:
        """Check if text is a slash command."""
        return text.startswith("/")

    def handle_slash_command(self, command: str) -> Optional[str]:
        """
        Handle a slash command.

        Args:
            command: Slash command string

        Returns:
            Command result or None
        """
        cmd, args = parse_slash_command(command)

        if cmd == "help":
            self._output.write(get_help_text())
            self._output.write("\n")
            return "help"

        elif cmd == "clear":
            self._agent.reset()
            self._output.write("Conversation cleared.\n")
            return "clear"

        elif cmd == "history":
            for i, item in enumerate(self._history._history[-10:]):
                self._output.write(f"{i+1}. {item}\n")
            return "history"

        elif cmd == "reset":
            self._agent.reset()
            self._history = REPLHistory(
                file_path=self._config.history_file,
                max_size=self._config.max_history,
            )
            self._output.write("Session reset.\n")
            return "reset"

        elif cmd in ("exit", "quit"):
            self._running = False
            return "exit"

        else:
            self._output.write(f"Unknown command: /{cmd}\n")
            self._output.write("Type /help for available commands.\n")
            return None

    def run(self) -> None:
        """Run the REPL loop."""
        self._running = True

        if self._config.show_welcome:
            self._print_welcome()

        while self._running:
            try:
                # Get input
                user_input = self._get_input()

                if user_input is None:
                    # EOF
                    break

                self.process_input(user_input)

            except KeyboardInterrupt:
                self._output.write("\n")
                continue
            except EOFError:
                break

        # Save history on exit
        self._history.save()
        self._output.write("Goodbye!\n")

    def _get_input(self) -> Optional[str]:
        """Get input from user."""
        try:
            line = input(self._config.prompt)

            # Handle multiline input
            while needs_continuation(line):
                continuation = input(self._config.continuation_prompt)
                line = line + "\n" + continuation

            return line
        except EOFError:
            return None

    def _print_response(self, result: Any) -> None:
        """Print agent response."""
        content = getattr(result, "content", str(result))
        if content:
            self._output.write(content)
            if not content.endswith("\n"):
                self._output.write("\n")
            self._output.flush()

    def _print_error(self, message: str) -> None:
        """Print error message."""
        self._output.write(f"Error: {message}\n")
        self._output.flush()

    def _print_welcome(self) -> None:
        """Print welcome message."""
        self._output.write("DeepCode Interactive Session\n")
        self._output.write("Type /help for commands, /exit to quit.\n")
        self._output.write("\n")
        self._output.flush()


# ===== Helper Functions =====


def is_multiline_input(text: str) -> bool:
    """Check if text contains multiple lines."""
    return "\n" in text


def needs_continuation(text: str) -> bool:
    """
    Check if input needs continuation.

    Args:
        text: Input text

    Returns:
        True if continuation needed
    """
    text = text.rstrip()

    # Backslash continuation
    if text.endswith("\\"):
        return True

    # Python-style block continuation
    if text.endswith(":"):
        return True

    # Unclosed brackets (simple check)
    open_count = text.count("(") + text.count("[") + text.count("{")
    close_count = text.count(")") + text.count("]") + text.count("}")
    if open_count > close_count:
        return True

    return False


def strip_input(text: str) -> str:
    """
    Strip and clean input text.

    Args:
        text: Input text

    Returns:
        Cleaned text
    """
    return text.strip()


def get_prompt(prefix: str = "") -> str:
    """
    Get the prompt string.

    Args:
        prefix: Optional prefix

    Returns:
        Prompt string
    """
    if prefix:
        return f"{prefix}> "
    return "> "


def get_continuation_prompt() -> str:
    """Get continuation prompt."""
    return "... "


def parse_slash_command(command: str) -> Tuple[str, List[str]]:
    """
    Parse a slash command.

    Args:
        command: Command string (e.g., "/help" or "/read file.txt")

    Returns:
        Tuple of (command_name, arguments)
    """
    parts = command.lstrip("/").split()
    if not parts:
        return "", []

    cmd = parts[0].lower()
    args = parts[1:]

    return cmd, args


def get_available_commands() -> Dict[str, str]:
    """
    Get available slash commands.

    Returns:
        Dictionary of command -> description
    """
    return REPLSession.SLASH_COMMANDS.copy()


def get_help_text() -> str:
    """
    Get help text for REPL.

    Returns:
        Help text string
    """
    lines = [
        "DeepCode REPL Commands:",
        "",
        "  /help     - Show this help message",
        "  /clear    - Clear conversation history",
        "  /history  - Show command history",
        "  /reset    - Reset the session",
        "  /exit     - Exit the REPL",
        "",
        "Tips:",
        "  - Use Ctrl+C to cancel current input",
        "  - Use Ctrl+D to exit",
        "  - Lines ending with : or \\ continue on next line",
        "",
    ]
    return "\n".join(lines)


def create_repl(
    agent: Any,
    history_file: Optional[str] = None,
    **kwargs: Any,
) -> REPLSession:
    """
    Create a REPL session.

    Args:
        agent: Agent instance
        history_file: Optional history file path
        **kwargs: Additional config options

    Returns:
        REPLSession instance
    """
    config = REPLConfig(
        agent=agent,
        history_file=history_file,
        **kwargs,
    )
    return REPLSession(config)
