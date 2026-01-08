"""
Tests for /rewind command - T073

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from pathlib import Path
from typing import List, Optional

import pytest

from claude_code.security.checkpoint import (
    CheckpointManager,
    CheckpointNotFoundError,
)
from claude_code.core.agent import Agent, AgentConfig, Message, MessageRole
from claude_code.cli.rewind import (
    RewindMode,
    RewindResult,
    RewindError,
    rewind_command,
    create_rewind_manager,
    RewindManager,
)


class TestRewindMode:
    """Test RewindMode enum."""

    def test_rewind_mode_values(self) -> None:
        """Test rewind mode enum values."""
        assert RewindMode.CONVERSATION.value == "conversation"
        assert RewindMode.CODE.value == "code"
        assert RewindMode.BOTH.value == "both"


class TestRewindResult:
    """Test RewindResult dataclass."""

    def test_rewind_result_success(self) -> None:
        """Test successful rewind result."""
        result = RewindResult(
            success=True,
            mode=RewindMode.CONVERSATION,
            checkpoint_name="test-checkpoint",
            messages_restored=5,
        )

        assert result.success is True
        assert result.mode == RewindMode.CONVERSATION
        assert result.checkpoint_name == "test-checkpoint"
        assert result.messages_restored == 5
        assert result.error is None

    def test_rewind_result_failure(self) -> None:
        """Test failed rewind result."""
        result = RewindResult(
            success=False,
            mode=RewindMode.BOTH,
            checkpoint_name="bad-checkpoint",
            messages_restored=0,
            error="Checkpoint not found",
        )

        assert result.success is False
        assert result.error == "Checkpoint not found"


class TestRewindManager:
    """Test RewindManager."""

    def test_create_rewind_manager(self, tmp_path: Path) -> None:
        """Test creating RewindManager."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        assert rewind_manager.checkpoint_manager == checkpoint_manager

    def test_rewind_conversation(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewinding conversation history."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        # Create checkpoint
        checkpoint_manager.create("test-conv", sample_history)

        # Create agent with some history
        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore
        for msg in sample_history:
            agent._history.append(msg)

        # Add more messages to agent
        agent._add_user_message("New message after checkpoint")
        agent._add_assistant_message("New response")

        # Rewind
        result = rewind_manager.rewind(
            mode=RewindMode.CONVERSATION,
            checkpoint_name="test-conv",
            agent=agent,
        )

        assert result.success is True
        assert result.mode == RewindMode.CONVERSATION
        assert result.checkpoint_name == "test-conv"
        assert result.messages_restored == len(sample_history)

        # Verify agent was rewound
        restored_history = agent.get_history()
        assert len(restored_history) == len(sample_history)
        assert restored_history[-1].content == sample_history[-1].content

    def test_rewind_with_invalid_checkpoint(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewinding with invalid checkpoint name."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        # Try to rewind to nonexistent checkpoint
        with pytest.raises(RewindError) as exc_info:
            rewind_manager.rewind(
                mode=RewindMode.CONVERSATION,
                checkpoint_name="nonexistent",
                agent=agent,
            )

        assert "not found" in str(exc_info.value).lower()

    def test_rewind_code_mode(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewinding in CODE mode (MVP: same as CONVERSATION)."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        checkpoint_manager.create("code-checkpoint", sample_history)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        result = rewind_manager.rewind(
            mode=RewindMode.CODE,
            checkpoint_name="code-checkpoint",
            agent=agent,
        )

        assert result.success is True
        assert result.mode == RewindMode.CODE

    def test_rewind_both_mode(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewinding in BOTH mode (MVP: same as CONVERSATION)."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        checkpoint_manager.create("both-checkpoint", sample_history)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        result = rewind_manager.rewind(
            mode=RewindMode.BOTH,
            checkpoint_name="both-checkpoint",
            agent=agent,
        )

        assert result.success is True
        assert result.mode == RewindMode.BOTH

    def test_rewind_with_no_checkpoints(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewind when no checkpoints exist."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        with pytest.raises(RewindError) as exc_info:
            rewind_manager.rewind(
                mode=RewindMode.CONVERSATION,
                checkpoint_name="nonexistent",
                agent=agent,
            )

        assert "not found" in str(exc_info.value).lower()

    def test_list_available_checkpoints(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test listing available checkpoints for rewind."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        # Create checkpoints
        checkpoint_manager.create("checkpoint-1", sample_history)
        checkpoint_manager.create("checkpoint-2", sample_history)
        checkpoint_manager.create("checkpoint-3", sample_history)

        # List checkpoints
        checkpoints = rewind_manager.list_checkpoints()

        assert len(checkpoints) == 3
        assert "checkpoint-1" in checkpoints
        assert "checkpoint-2" in checkpoints
        assert "checkpoint-3" in checkpoints

    def test_has_checkpoint(self, tmp_path: Path, sample_history: List[Message]) -> None:
        """Test checking if checkpoint exists for rewind."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        assert not rewind_manager.has_checkpoint("test")

        checkpoint_manager.create("test", sample_history)

        assert rewind_manager.has_checkpoint("test")


class TestRewindCommand:
    """Test rewind command interface."""

    def test_create_rewind_manager_default(self) -> None:
        """Test creating rewind manager with default config."""
        manager = create_rewind_manager()

        assert manager is not None
        assert isinstance(manager, RewindManager)

    def test_rewind_command_conversation(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewind_command function for conversation mode."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        checkpoint_manager.create("conv-test", sample_history)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        result = rewind_command(
            mode="conversation",
            checkpoint_name="conv-test",
            agent=agent,
            checkpoint_manager=checkpoint_manager,
        )

        assert result.success is True
        assert result.mode == RewindMode.CONVERSATION
        assert result.checkpoint_name == "conv-test"

    def test_rewind_command_code(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewind_command function for code mode."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        checkpoint_manager.create("code-test", sample_history)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        result = rewind_command(
            mode="code",
            checkpoint_name="code-test",
            agent=agent,
            checkpoint_manager=checkpoint_manager,
        )

        assert result.success is True
        assert result.mode == RewindMode.CODE

    def test_rewind_command_both(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewind_command function for both mode."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        checkpoint_manager.create("both-test", sample_history)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        result = rewind_command(
            mode="both",
            checkpoint_name="both-test",
            agent=agent,
            checkpoint_manager=checkpoint_manager,
        )

        assert result.success is True
        assert result.mode == RewindMode.BOTH

    def test_rewind_command_invalid_mode(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewind_command with invalid mode."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        checkpoint_manager.create("test", sample_history)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        with pytest.raises(RewindError) as exc_info:
            rewind_command(
                mode="invalid",
                checkpoint_name="test",
                agent=agent,
                checkpoint_manager=checkpoint_manager,
            )

        assert "invalid rewind mode" in str(exc_info.value).lower()

    def test_rewind_command_checkpoint_not_found(
        self, tmp_path: Path, sample_history: List[Message]
    ) -> None:
        """Test rewind_command when checkpoint doesn't exist."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        with pytest.raises(RewindError) as exc_info:
            rewind_command(
                mode="conversation",
                checkpoint_name="nonexistent",
                agent=agent,
                checkpoint_manager=checkpoint_manager,
            )

        assert "not found" in str(exc_info.value).lower()


class TestRewindIntegration:
    """Integration tests for rewind functionality."""

    def test_full_rewind_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow: create checkpoint, modify, rewind."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        # Create agent with initial conversation
        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore
        agent._add_user_message("Initial question")
        agent._add_assistant_message("Initial answer")

        # Create checkpoint
        initial_history = agent.get_history()
        checkpoint_manager.create("initial-state", initial_history)

        # Continue conversation
        agent._add_user_message("Follow-up question")
        agent._add_assistant_message("Follow-up answer")

        # Verify we have 4 messages
        assert len(agent.get_history()) == 4

        # Rewind to checkpoint
        result = rewind_manager.rewind(
            mode=RewindMode.CONVERSATION,
            checkpoint_name="initial-state",
            agent=agent,
        )

        # Verify rewind worked
        assert result.success is True
        assert len(agent.get_history()) == 2  # Back to initial state

    def test_multiple_checkpoints_and_rewinds(self, tmp_path: Path) -> None:
        """Test creating multiple checkpoints and rewinding between them."""
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
        rewind_manager = RewindManager(checkpoint_manager=checkpoint_manager)

        agent = Agent(config=AgentConfig(llm_client=None))  # type: ignore

        # Build conversation and create checkpoints
        agent._add_user_message("Q1")
        agent._add_assistant_message("A1")
        checkpoint_manager.create("state-1", agent.get_history())

        agent._add_user_message("Q2")
        agent._add_assistant_message("A2")
        checkpoint_manager.create("state-2", agent.get_history())

        agent._add_user_message("Q3")
        agent._add_assistant_message("A3")
        checkpoint_manager.create("state-3", agent.get_history())

        # Rewind to state 2
        rewind_manager.rewind(RewindMode.CONVERSATION, "state-2", agent)
        assert len(agent.get_history()) == 4

        # Rewind to state 1
        rewind_manager.rewind(RewindMode.CONVERSATION, "state-1", agent)
        assert len(agent.get_history()) == 2

        # Restore to state 3
        rewind_manager.rewind(RewindMode.CONVERSATION, "state-3", agent)
        assert len(agent.get_history()) == 6


@pytest.fixture
def sample_history() -> List[Message]:
    """Create sample conversation history."""
    return [
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        Message(role=MessageRole.USER, content="How are you?"),
        Message(role=MessageRole.ASSISTANT, content="I'm doing well, thanks!"),
    ]
