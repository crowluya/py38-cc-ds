"""
Approval and selection wrapper using Questionary

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import logging
from typing import List, Optional

import colorama
import questionary
from questionary import select

# Initialize colorama for Windows 7 ANSI support
colorama.init()

_LOGGER = logging.getLogger(__name__)


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
            result = questionary.confirm(message, default=default).ask()
            return result if result is not None else default
        except KeyboardInterrupt:
            return default
        except EOFError:
            return default
        except Exception as e:
            _LOGGER.debug("confirm failed: %s", e)
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
        except KeyboardInterrupt:
            return None
        except EOFError:
            return None
        except Exception as e:
            _LOGGER.debug("select failed: %s", e)
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
        try:
            result = questionary.checkbox(
                message,
                choices=choices,
            ).ask()

            return result if result is not None else []
        except KeyboardInterrupt:
            return []
        except EOFError:
            return []
        except Exception as e:
            _LOGGER.debug("select_many failed: %s", e)
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
        try:
            result = questionary.autocomplete(
                message,
                choices=choices,
            ).ask()

            return result
        except KeyboardInterrupt:
            return None
        except EOFError:
            return None
        except Exception as e:
            _LOGGER.debug("autocomplete failed: %s", e)
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
        # Use questionary.print for consistent styling
        questionary.print("\n⚠️  DANGEROUS ACTION ⚠️", style="bold fg:red")
        questionary.print(f"Action: {action}", style="fg:yellow")

        if details:
            questionary.print(f"Details: {details}", style="fg:gray")

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
