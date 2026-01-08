"""
Rewind Command - T073

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Handles:
- /rewind command for rolling back conversation state
- Support for conversation/code/both rewind modes
- Integration with checkpoint manager
- Error handling for invalid checkpoints
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

from claude_code.security.checkpoint import CheckpointManager, CheckpointNotFoundError


class RewindError(Exception):
    """Base exception for rewind errors."""

    pass


class RewindMode(Enum):
    """Rewind mode types."""

    CONVERSATION = "conversation"
    CODE = "code"
    BOTH = "both"


@dataclass
class RewindResult:
    """
    Result of a rewind operation.

    Contains success status, mode used, checkpoint name, and metrics.
    """

    success: bool
    mode: RewindMode
    checkpoint_name: str
    messages_restored: int
    error: Optional[str] = None

    def __str__(self) -> str:
        """String representation."""
        if self.success:
            return (
                f"Rewind successful: {self.checkpoint_name} "
                f"({self.messages_restored} messages restored, mode={self.mode.value})"
            )
        else:
            return f"Rewind failed: {self.error}"


class RewindManager:
    """
    Manages rewind operations.

    Features:
    - Rewind conversation history to checkpoint
    - Support for different rewind modes (conversation/code/both)
    - Integration with checkpoint manager
    - Error handling and validation
    """

    def __init__(self, checkpoint_manager: CheckpointManager) -> None:
        """
        Initialize RewindManager.

        Args:
            checkpoint_manager: CheckpointManager instance
        """
        self.checkpoint_manager = checkpoint_manager

    def rewind(
        self,
        mode: RewindMode,
        checkpoint_name: str,
        agent: Any,
    ) -> RewindResult:
        """
        Perform rewind operation.

        Args:
            mode: Rewind mode (conversation/code/both)
            checkpoint_name: Name of checkpoint to rewind to
            agent: Agent instance to restore

        Returns:
            RewindResult with operation details

        Raises:
            RewindError: If rewind operation fails
        """
        # Check if checkpoint exists
        if not self.checkpoint_manager.has(checkpoint_name):
            raise RewindError(f"Checkpoint '{checkpoint_name}' not found")

        # Load checkpoint
        checkpoint = self.checkpoint_manager.get(checkpoint_name)

        # Restore to agent based on mode
        try:
            if mode == RewindMode.CONVERSATION:
                messages_count = self._rewind_conversation(checkpoint, agent)
            elif mode == RewindMode.CODE:
                # MVP: CODE mode behaves like CONVERSATION
                # Future: could track file changes separately
                messages_count = self._rewind_conversation(checkpoint, agent)
            elif mode == RewindMode.BOTH:
                # MVP: BOTH mode behaves like CONVERSATION
                # Future: could rewind conversation + files separately
                messages_count = self._rewind_conversation(checkpoint, agent)
            else:
                raise RewindError(f"Invalid rewind mode: {mode}")

            return RewindResult(
                success=True,
                mode=mode,
                checkpoint_name=checkpoint_name,
                messages_restored=messages_count,
            )
        except Exception as e:
            raise RewindError(f"Failed to rewind: {e}")

    def _rewind_conversation(self, checkpoint: Any, agent: Any) -> int:
        """
        Rewind conversation history.

        Args:
            checkpoint: Checkpoint to restore from
            agent: Agent instance

        Returns:
            Number of messages restored
        """
        # Get history from checkpoint
        history = checkpoint.history

        # Restore to agent
        if hasattr(agent, "_history"):
            # Direct assignment (faster than clearing and adding)
            agent._history = list(history)
        elif hasattr(agent, "clear_history") and hasattr(agent, "add_message"):
            # Use agent's methods if available
            agent.clear_history()
            for msg in history:
                agent.add_message(msg)
        else:
            raise RewindError("Agent does not support history restoration")

        return len(history)

    def list_checkpoints(self) -> List[str]:
        """
        List available checkpoints for rewinding.

        Returns:
            List of checkpoint names
        """
        return self.checkpoint_manager.list_checkpoints()

    def has_checkpoint(self, name: str) -> bool:
        """
        Check if checkpoint exists.

        Args:
            name: Checkpoint name

        Returns:
            True if checkpoint exists
        """
        return self.checkpoint_manager.has(name)


def create_rewind_manager(
    checkpoint_dir: Optional[Path] = None,
) -> RewindManager:
    """
    Create a RewindManager with default configuration.

    Uses default checkpoint directory (.claude/checkpoints/).

    Args:
        checkpoint_dir: Optional checkpoint directory (defaults to .claude/checkpoints/)

    Returns:
        Configured RewindManager
    """
    if checkpoint_dir is None:
        # Use default checkpoint manager
        checkpoint_manager = CheckpointManager(project_path=Path.cwd())
    else:
        checkpoint_manager = CheckpointManager(checkpoint_dir=checkpoint_dir)

    return RewindManager(checkpoint_manager=checkpoint_manager)


def rewind_command(
    mode: str,
    checkpoint_name: str,
    agent: Any,
    checkpoint_manager: Optional[CheckpointManager] = None,
) -> RewindResult:
    """
    Execute rewind command.

    Convenience function for executing rewind from slash commands or CLI.

    Args:
        mode: Rewind mode ("conversation", "code", or "both")
        checkpoint_name: Name of checkpoint to rewind to
        agent: Agent instance to restore
        checkpoint_manager: Optional CheckpointManager (uses default if None)

    Returns:
        RewindResult with operation details

    Raises:
        RewindError: If rewind operation fails
    """
    # Parse mode
    try:
        rewind_mode = RewindMode(mode.lower())
    except ValueError:
        raise RewindError(f"Invalid rewind mode: {mode}. Must be one of: conversation, code, both")

    # Create checkpoint manager if not provided
    if checkpoint_manager is None:
        checkpoint_manager = CheckpointManager(project_path=Path.cwd())

    # Create rewind manager
    rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

    # Execute rewind
    return rewind_manager.rewind(
        mode=rewind_mode,
        checkpoint_name=checkpoint_name,
        agent=agent,
    )
