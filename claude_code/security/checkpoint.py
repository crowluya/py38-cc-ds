"""
Checkpoint manager - T072

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Handles:
- Session checkpoint creation
- Checkpoint listing and retrieval
- Rollback to previous conversation state
- JSON persistence
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import json

from claude_code.config.constants import get_project_checkpoints_dir


class CheckpointError(Exception):
    """Base exception for checkpoint errors."""


class CheckpointNotFoundError(CheckpointError):
    """Raised when a checkpoint is not found."""

    def __init__(self, name: str) -> None:
        """
        Initialize error.

        Args:
            name: Checkpoint name that was not found
        """
        self.name = name
        super().__init__(f"Checkpoint not found: {name}")


class CheckpointExistsError(CheckpointError):
    """Raised when trying to create a duplicate checkpoint."""

    def __init__(self, name: str) -> None:
        """
        Initialize error.

        Args:
            name: Checkpoint name that already exists
        """
        self.name = name
        super().__init__(f"Checkpoint already exists: {name}")


@dataclass
class Checkpoint:
    """
    A checkpoint capturing conversation state.

    Contains:
    - Name: Unique identifier
    - Timestamp: When checkpoint was created
    - History: Conversation messages
    - Metadata: Optional additional information
    """

    name: str
    history: List[Any]  # List[Message] but avoiding circular import
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert checkpoint to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "history": [msg.to_dict() for msg in self.history],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """
        Create checkpoint from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Checkpoint instance
        """
        # Avoid circular import
        from claude_code.core.agent import Message

        history = [Message.from_dict(item) for item in data.get("history", [])]

        return cls(
            name=data["name"],
            history=history,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata"),
        )

    def save(self, path: Path) -> None:
        """
        Save checkpoint to file.

        Args:
            path: File path to save to
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> "Checkpoint":
        """
        Load checkpoint from file.

        Args:
            path: File path to load from

        Returns:
            Checkpoint instance

        Raises:
            CheckpointError: If file doesn't exist or is invalid
        """
        if not path.exists():
            raise CheckpointError(f"Checkpoint file not found: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise CheckpointError(f"Invalid checkpoint file: {path}: {e}")


class CheckpointManager:
    """
    Manages conversation checkpoints.

    Features:
    - Create checkpoints with conversation history
    - List all available checkpoints
    - Retrieve specific checkpoints
    - Delete checkpoints
    - Rollback to previous state
    - JSON persistence
    """

    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> None:
        """
        Initialize CheckpointManager.

        Args:
            checkpoint_dir: Directory to store checkpoints (optional)
            project_path: Project path, uses .my-claude/checkpoints if provided (optional)

        Raises:
            ValueError: If neither checkpoint_dir nor project_path is provided
        """
        if checkpoint_dir is None:
            if project_path is None:
                raise ValueError("Must provide either checkpoint_dir or project_path")
            checkpoint_dir = get_project_checkpoints_dir(project_path)

        self.checkpoint_dir: Path = checkpoint_dir

        # Create directory if it doesn't exist
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        name: str,
        history: List[Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """
        Create a new checkpoint.

        Args:
            name: Checkpoint name
            history: Conversation history (list of Message objects)
            metadata: Optional metadata

        Returns:
            Created Checkpoint

        Raises:
            CheckpointExistsError: If checkpoint with name already exists
        """
        checkpoint_file = self.checkpoint_dir / f"{name}.json"

        # Check if checkpoint already exists
        if checkpoint_file.exists():
            raise CheckpointExistsError(name)

        # Create checkpoint
        checkpoint = Checkpoint(
            name=name,
            history=history,
            timestamp=datetime.now(),
            metadata=metadata,
        )

        # Save to file
        checkpoint.save(checkpoint_file)

        return checkpoint

    def list_checkpoints(self) -> List[str]:
        """
        List all checkpoint names.

        Returns:
            List of checkpoint names
        """
        if not self.checkpoint_dir.exists():
            return []

        checkpoint_files = list(self.checkpoint_dir.glob("*.json"))
        return [
            f.stem for f in checkpoint_files if f.is_file()
        ]

    def get(self, name: str) -> Checkpoint:
        """
        Get a checkpoint by name.

        Args:
            name: Checkpoint name

        Returns:
            Checkpoint instance

        Raises:
            CheckpointNotFoundError: If checkpoint doesn't exist
        """
        checkpoint_file = self.checkpoint_dir / f"{name}.json"

        if not checkpoint_file.exists():
            raise CheckpointNotFoundError(name)

        return Checkpoint.load(checkpoint_file)

    def has(self, name: str) -> bool:
        """
        Check if checkpoint exists.

        Args:
            name: Checkpoint name

        Returns:
            True if checkpoint exists
        """
        checkpoint_file = self.checkpoint_dir / f"{name}.json"
        return checkpoint_file.exists()

    def delete(self, name: str) -> None:
        """
        Delete a checkpoint.

        Args:
            name: Checkpoint name

        Raises:
            CheckpointNotFoundError: If checkpoint doesn't exist
        """
        checkpoint_file = self.checkpoint_dir / f"{name}.json"

        if not checkpoint_file.exists():
            raise CheckpointNotFoundError(name)

        checkpoint_file.unlink()

    def restore_to_agent(self, name: str, agent: Any) -> None:
        """
        Restore checkpoint to agent.

        Args:
            name: Checkpoint name
            agent: Agent instance to restore to

        Raises:
            CheckpointNotFoundError: If checkpoint doesn't exist
        """
        checkpoint = self.get(name)

        # Reset agent's current history
        agent.reset()

        # Restore messages from checkpoint
        # Directly set _history since Agent doesn't have a public add_message method
        agent._history = list(checkpoint.history)

    def rollback(self, name: str) -> List[Any]:
        """
        Rollback to checkpoint (returns conversation history).

        Args:
            name: Checkpoint name

        Returns:
            List of Message objects

        Raises:
            CheckpointNotFoundError: If checkpoint doesn't exist
        """
        checkpoint = self.get(name)
        return checkpoint.history
