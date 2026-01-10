"""
Tests for checkpoint manager - T072

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import pytest

from deep_code.security.checkpoint import (
    Checkpoint,
    CheckpointManager,
    CheckpointError,
    CheckpointExistsError,
    CheckpointNotFoundError,
)
from deep_code.core.agent import Message, MessageRole, serialize_history, deserialize_history


class TestCheckpoint:
    """Test Checkpoint dataclass."""

    def test_create_checkpoint(self) -> None:
        """Test creating a checkpoint."""
        history = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there"),
        ]

        checkpoint = Checkpoint(
            name="test-checkpoint",
            history=history,
            timestamp=datetime.now(),
        )

        assert checkpoint.name == "test-checkpoint"
        assert len(checkpoint.history) == 2
        assert checkpoint.history[0].content == "Hello"

    def test_serialize_checkpoint(self, tmp_path: Path) -> None:
        """Test serializing checkpoint to file."""
        history = [
            Message(role=MessageRole.USER, content="Test message"),
        ]

        checkpoint = Checkpoint(
            name="serialize-test",
            history=history,
            timestamp=datetime.now(),
        )

        # Save to file
        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint.save(checkpoint_file)

        # Verify file exists
        assert checkpoint_file.exists()

        # Verify content
        data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        assert data["name"] == "serialize-test"
        assert "history" in data
        assert "timestamp" in data

    def test_deserialize_checkpoint(self, tmp_path: Path) -> None:
        """Test loading checkpoint from file."""
        # Create checkpoint file
        history_data = [
            {
                "role": "user",
                "content": "Loaded message",
                "tool_result": None,
                "metadata": None,
            }
        ]

        data = {
            "name": "load-test",
            "timestamp": datetime.now().isoformat(),
            "history": history_data,
        }

        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint_file.write_text(json.dumps(data), encoding="utf-8")

        # Load checkpoint
        checkpoint = Checkpoint.load(checkpoint_file)

        assert checkpoint.name == "load-test"
        assert len(checkpoint.history) == 1
        assert checkpoint.history[0].content == "Loaded message"

    def test_deserialize_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading from nonexistent file raises error."""
        with pytest.raises(CheckpointError):
            Checkpoint.load(tmp_path / "nonexistent.json")


class TestCheckpointManager:
    """Test CheckpointManager."""

    def test_create_manager(self, tmp_path: Path) -> None:
        """Test creating checkpoint manager."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        assert manager.checkpoint_dir == tmp_path
        assert len(manager.list_checkpoints()) == 0

    def test_create_checkpoint(self, tmp_path: Path) -> None:
        """Test creating a checkpoint."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        history = [
            Message(role=MessageRole.USER, content="First message"),
            Message(role=MessageRole.ASSISTANT, content="First response"),
        ]

        checkpoint = manager.create("test-checkpoint", history)

        assert checkpoint.name == "test-checkpoint"
        assert len(checkpoint.history) == 2

        # Verify file was created
        checkpoint_file = tmp_path / "test-checkpoint.json"
        assert checkpoint_file.exists()

    def test_create_duplicate_checkpoint_raises(self, tmp_path: Path) -> None:
        """Test creating duplicate checkpoint raises error."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        history = [Message(role=MessageRole.USER, content="Test")]

        # Create first checkpoint
        manager.create("test", history)

        # Try to create duplicate
        with pytest.raises(CheckpointExistsError):
            manager.create("test", history)

    def test_list_checkpoints(self, tmp_path: Path) -> None:
        """Test listing checkpoints."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        history = [Message(role=MessageRole.USER, content="Test")]

        # Create multiple checkpoints
        manager.create("checkpoint-1", history)
        manager.create("checkpoint-2", history)
        manager.create("checkpoint-3", history)

        # List checkpoints
        checkpoints = manager.list_checkpoints()

        assert len(checkpoints) == 3
        assert "checkpoint-1" in checkpoints
        assert "checkpoint-2" in checkpoints
        assert "checkpoint-3" in checkpoints

    def test_list_checkpoints_empty(self, tmp_path: Path) -> None:
        """Test listing checkpoints when none exist."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        checkpoints = manager.list_checkpoints()

        assert checkpoints == []

    def test_get_checkpoint(self, tmp_path: Path) -> None:
        """Test getting a checkpoint by name."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        history = [
            Message(role=MessageRole.USER, content="Retrieve test"),
        ]

        manager.create("get-test", history)

        # Get checkpoint
        checkpoint = manager.get("get-test")

        assert checkpoint is not None
        assert checkpoint.name == "get-test"
        assert checkpoint.history[0].content == "Retrieve test"

    def test_get_nonexistent_checkpoint(self, tmp_path: Path) -> None:
        """Test getting nonexistent checkpoint raises error."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        with pytest.raises(CheckpointNotFoundError):
            manager.get("nonexistent")

    def test_has_checkpoint(self, tmp_path: Path) -> None:
        """Test checking if checkpoint exists."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        history = [Message(role=MessageRole.USER, content="Test")]

        assert not manager.has("test")

        manager.create("test", history)

        assert manager.has("test")

    def test_delete_checkpoint(self, tmp_path: Path) -> None:
        """Test deleting a checkpoint."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        history = [Message(role=MessageRole.USER, content="Delete test")]

        manager.create("delete-test", history)

        # Verify it exists
        assert manager.has("delete-test")

        # Delete it
        manager.delete("delete-test")

        # Verify it's gone
        assert not manager.has("delete-test")

    def test_delete_nonexistent_checkpoint(self, tmp_path: Path) -> None:
        """Test deleting nonexistent checkpoint raises error."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        with pytest.raises(CheckpointNotFoundError):
            manager.delete("nonexistent")

    def test_load_checkpoint_to_agent(self, tmp_path: Path) -> None:
        """Test loading checkpoint restores conversation history."""
        from deep_code.core.agent import Agent, AgentConfig

        manager = CheckpointManager(checkpoint_dir=tmp_path)

        # Create checkpoint with history
        history = [
            Message(role=MessageRole.USER, content="Question 1"),
            Message(role=MessageRole.ASSISTANT, content="Answer 1"),
            Message(role=MessageRole.USER, content="Question 2"),
            Message(role=MessageRole.ASSISTANT, content="Answer 2"),
        ]

        manager.create("qa-checkpoint", history)

        # Create agent and load checkpoint
        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore
        manager.restore_to_agent("qa-checkpoint", agent)

        # Verify history was restored
        restored_history = agent.get_history()
        assert len(restored_history) == 4
        assert restored_history[0].content == "Question 1"
        assert restored_history[1].content == "Answer 1"
        assert restored_history[2].content == "Question 2"
        assert restored_history[3].content == "Answer 2"

    def test_checkpoint_metadata(self, tmp_path: Path) -> None:
        """Test checkpoint with metadata."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        history = [Message(role=MessageRole.USER, content="Test")]
        metadata = {
            "model": "deepseek-r1",
            "temperature": 0.7,
            "tags": ["test", "example"],
        }

        checkpoint = manager.create("metadata-test", history, metadata=metadata)

        assert checkpoint.metadata == metadata

        # Verify metadata persists after reload
        reloaded = manager.get("metadata-test")
        assert reloaded.metadata == metadata


@pytest.fixture
def sample_history() -> List[Message]:
    """Create sample conversation history."""
    return [
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        Message(role=MessageRole.USER, content="How are you?"),
        Message(role=MessageRole.ASSISTANT, content="I'm doing well, thanks!"),
    ]
