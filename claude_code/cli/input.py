"""
Interactive input wrapper using Prompt Toolkit

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from typing import Callable, List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition


class Input:
    """
    Interactive input wrapper using Prompt Toolkit.

    Features:
    - Multi-line input (Shift+Enter to submit)
    - History support (file-based)
    - Auto-suggest from history
    - Custom key bindings
    """

    def __init__(
        self,
        history_path: Optional[str] = None,
        session: Optional[PromptSession] = None,
    ):
        """
        Initialize Input wrapper.

        Args:
            history_path: Path to history file (optional)
            session: PromptSession for dependency injection (testing)
        """
        self._history_path = history_path
        self._session = session

    def _get_session(self) -> PromptSession:
        """Get or create PromptSession."""
        if self._session is not None:
            return self._session

        kwargs = {}
        if self._history_path:
            kwargs["history"] = FileHistory(self._history_path)

        self._session = PromptSession(**kwargs)
        return self._session

    def prompt(
        self,
        message: str = "> ",
        multiline: bool = False,
        password: bool = False,
    ) -> str:
        """
        Get user input.

        Args:
            message: Prompt message
            multiline: Enable multi-line input (Shift+Enter to submit)
            password: Hide input (password mode)

        Returns:
            User input string
        """
        session = self._get_session()

        if password:
            return session.prompt(message, is_password=True)
        elif multiline:
            return session.prompt(message, multiline=True)
        else:
            return session.prompt(message)

    def prompt_with_completer(
        self,
        message: str,
        completions: List[str],
    ) -> str:
        """
        Get user input with auto-completion.

        Args:
            message: Prompt message
            completions: List of completion words

        Returns:
            User input string
        """
        session = self._get_session()
        completer = WordCompleter(completions)

        return session.prompt(message, completer=completer)

    def confirm(
        self,
        message: str,
        default: bool = False,
    ) -> bool:
        """
        Get yes/no confirmation.

        Args:
            message: Confirmation message
            default: Default value if user just presses Enter

        Returns:
            True if user confirms, False otherwise
        """
        prompt_text = f"{message} [{'Y/n' if default else 'y/N'}]: "
        response = self.prompt(prompt_text).strip().lower()

        if not response:
            return default

        return response in ("y", "yes")

    def select(
        self,
        message: str,
        choices: List[str],
    ) -> Optional[int]:
        """
        Let user select from a list (simplified - type number).

        Args:
            message: Selection message
            choices: List of choices

        Returns:
            Selected index (0-based), or None if cancelled
        """
        for i, choice in enumerate(choices):
            self.print(f"  {i + 1}. {choice}")

        response = self.prompt(f"{message} (1-{len(choices)}, 0 to cancel): ")
        try:
            index = int(response.strip())
            if index == 0:
                return None
            if 1 <= index <= len(choices):
                return index - 1
            return None
        except ValueError:
            return None

    def print(self, text: str) -> None:
        """Print text (for select menu display)."""
        from prompt_toolkit import print_formatted_text

        print_formatted_text(text)


# Default singleton
_default_input: Optional[Input] = None


def get_input(history_path: Optional[str] = None) -> Input:
    """Get the default Input instance."""
    global _default_input
    if _default_input is None:
        _default_input = Input(history_path=history_path)
    return _default_input


def set_input(input_instance: Input) -> None:
    """Set the default Input instance (for testing)."""
    global _default_input
    _default_input = input_instance
