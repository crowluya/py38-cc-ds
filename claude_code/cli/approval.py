"""
Approval and selection wrapper using Questionary

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from typing import Any, Callable, List, Optional, TypeVar

import colorama
from questionary import Choice, Form, confirm, select

# Initialize colorama for Windows 7 ANSI support
colorama.init()


T = TypeVar("T")


class Approval:
    """
    Approval and selection wrapper using Questionary.

    Features:
    - Yes/no confirmation prompts
    - Single selection menus
    - Multiple selection menus
    - Form input
    - Windows 7 ANSI color support via colorama
    """

    def __init__(self) -> None:
        """Initialize Approval wrapper."""
        # colorama already initialized at module level

    def confirm(
        self,
        message: str,
        default: bool = False,
    ) -> bool:
        """
        Ask for yes/no confirmation.

        Args:
            message: Confirmation message
            default: Default value (True for yes, False for no)

        Returns:
            True if user confirms, False otherwise
        """
        try:
            result = confirm(message, default=default).ask()
            return result if result is not None else default
        except Exception:
            # Fallback to default on error
            return default

    def select(
        self,
        message: str,
        choices: List[str],
        default: Optional[str] = None,
    ) -> Optional[str]:
        """
        Single selection from a list.

        Args:
            message: Selection message
            choices: List of choice strings
            default: Default choice (optional)

        Returns:
            Selected choice string, or None if cancelled
        """
        try:
            result = select(
                message,
                choices=choices,
                default=default,
            ).ask()

            return result
        except Exception:
            return None

    def select_many(
        self,
        message: str,
        choices: List[str],
    ) -> List[str]:
        """
        Multiple selection from a list.

        Args:
            message: Selection message
            choices: List of choice strings

        Returns:
            List of selected choice strings
        """
        from questionary import checkbox

        try:
            result = checkbox(
                message,
                choices=choices,
            ).ask()

            return result if result is not None else []
        except Exception:
            return []

    def autocomplete(
        self,
        message: str,
        choices: List[str],
    ) -> Optional[str]:
        """
        Autocomplete selection.

        Args:
            message: Selection message
            choices: List of choice strings

        Returns:
            Selected choice string, or None if cancelled
        """
        from questionary import autocomplete

        try:
            result = autocomplete(
                message,
                choices=choices,
            ).ask()

            return result
        except Exception:
            return None

    def dangerous_action_confirm(
        self,
        action: str,
        details: Optional[str] = None,
    ) -> bool:
        """
        Confirm a dangerous action (e.g., file deletion, force push).

        Args:
            action: Description of the action
            details: Optional details about what will happen

        Returns:
            True if user confirms, False otherwise
        """
        import click

        click.secho("\n⚠️  DANGEROUS ACTION ⚠️", fg="red", bold=True)
        click.echo(f"Action: {action}")

        if details:
            click.echo(f"Details: {details}")

        # Double confirmation for dangerous actions
        first = self.confirm("Are you sure you want to proceed?", default=False)
        if not first:
            return False

        return self.confirm("This action cannot be undone. Continue?", default=False)

    def approve_file_operation(
        self,
        operation: str,
        file_path: str,
    ) -> bool:
        """
        Approve a file operation (read/write/edit).

        Args:
            operation: Operation type ("read", "write", "edit")
            file_path: Path to the file

        Returns:
            True if user approves, False otherwise
        """
        import click

        emoji = {
            "read": "📖",
            "write": "✏️",
            "edit": "📝",
        }.get(operation, "⚙️")

        message = f"{emoji} {operation.capitalize()}: {file_path}"
        return self.confirm(message, default=True)


# Default singleton
_default_approval: Optional[Approval] = None


def get_approval() -> Approval:
    """Get the default Approval instance."""
    global _default_approval
    if _default_approval is None:
        _default_approval = Approval()
    return _default_approval
