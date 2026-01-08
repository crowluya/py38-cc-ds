"""
Example: Using /rewind command - T073

This example demonstrates how to use the rewind functionality
to rollback conversation state to a previous checkpoint.

Python 3.8.10 compatible
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from claude_code.core.agent import Agent, AgentConfig, Message, MessageRole
from claude_code.security.checkpoint import CheckpointManager
from claude_code.cli.rewind import rewind_command, RewindMode, RewindError


def example_basic_rewind():
    """Example: Basic rewind workflow."""
    print("=" * 60)
    print("Example 1: Basic Rewind Workflow")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Setup
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmpdir)
        agent = Agent(config=AgentConfig(llm_client=None))  # Fake LLM for demo

        # Simulate conversation
        print("\n1. Building initial conversation...")
        agent._add_user_message("What is Python?")
        agent._add_assistant_message("Python is a programming language.")
        print(f"   Messages: {len(agent.get_history())}")

        # Create checkpoint
        print("\n2. Creating checkpoint 'initial'...")
        checkpoint_manager.create("initial", agent.get_history())
        print("   Checkpoint created!")

        # Continue conversation
        print("\n3. Continuing conversation...")
        agent._add_user_message("How do I install it?")
        agent._add_assistant_message("Use pip to install Python packages.")
        print(f"   Messages: {len(agent.get_history())}")

        # Rewind to checkpoint
        print("\n4. Rewinding to checkpoint 'initial'...")
        result = rewind_command(
            mode="conversation",
            checkpoint_name="initial",
            agent=agent,
            checkpoint_manager=checkpoint_manager,
        )

        print(f"   Result: {result}")
        print(f"   Messages after rewind: {len(agent.get_history())}")


def example_multiple_checkpoints():
    """Example: Multiple checkpoints and switching between them."""
    print("\n" + "=" * 60)
    print("Example 2: Multiple Checkpoints")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Setup
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmpdir)
        agent = Agent(config=AgentConfig(llm_client=None))

        # Build conversation with checkpoints
        print("\n1. Building conversation with checkpoints...")

        agent._add_user_message("Q1")
        agent._add_assistant_message("A1")
        checkpoint_manager.create("state-1", agent.get_history())
        print(f"   Created checkpoint 'state-1' (2 messages)")

        agent._add_user_message("Q2")
        agent._add_assistant_message("A2")
        checkpoint_manager.create("state-2", agent.get_history())
        print(f"   Created checkpoint 'state-2' (4 messages)")

        agent._add_user_message("Q3")
        agent._add_assistant_message("A3")
        checkpoint_manager.create("state-3", agent.get_history())
        print(f"   Created checkpoint 'state-3' (6 messages)")

        # Rewind between checkpoints
        print("\n2. Rewinding to different checkpoints...")

        rewind_command("conversation", "state-1", agent, checkpoint_manager)
        print(f"   Rewound to 'state-1': {len(agent.get_history())} messages")

        rewind_command("conversation", "state-3", agent, checkpoint_manager)
        print(f"   Rewound to 'state-3': {len(agent.get_history())} messages")

        rewind_command("conversation", "state-2", agent, checkpoint_manager)
        print(f"   Rewound to 'state-2': {len(agent.get_history())} messages")


def example_rewind_modes():
    """Example: Different rewind modes."""
    print("\n" + "=" * 60)
    print("Example 3: Rewind Modes")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Setup
        checkpoint_manager = CheckpointManager(checkpoint_dir=tmpdir)
        agent = Agent(config=AgentConfig(llm_client=None))

        # Create checkpoint
        agent._add_user_message("Test message")
        checkpoint_manager.create("test", agent.get_history())

        # Test different modes
        print("\n1. Rewind mode: CONVERSATION")
        result = rewind_command("conversation", "test", agent, checkpoint_manager)
        print(f"   {result}")

        print("\n2. Rewind mode: CODE")
        result = rewind_command("code", "test", agent, checkpoint_manager)
        print(f"   {result}")

        print("\n3. Rewind mode: BOTH")
        result = rewind_command("both", "test", agent, checkpoint_manager)
        print(f"   {result}")


def example_error_handling():
    """Example: Error handling."""
    print("\n" + "=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        checkpoint_manager = CheckpointManager(checkpoint_dir=tmpdir)
        agent = Agent(config=AgentConfig(llm_client=None))

        # Try to rewind to nonexistent checkpoint
        print("\n1. Attempting to rewind to nonexistent checkpoint...")
        try:
            rewind_command("conversation", "nonexistent", agent, checkpoint_manager)
        except RewindError as e:
            print(f"   Error caught: {e}")

        # Try invalid mode
        print("\n2. Attempting to use invalid rewind mode...")
        try:
            rewind_command("invalid_mode", "test", agent, checkpoint_manager)
        except RewindError as e:
            print(f"   Error caught: {e}")


def example_list_checkpoints():
    """Example: Listing available checkpoints."""
    print("\n" + "=" * 60)
    print("Example 5: Listing Checkpoints")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        checkpoint_manager = CheckpointManager(checkpoint_dir=tmpdir)
        agent = Agent(config=AgentConfig(llm_client=None))

        # Create checkpoints
        print("\n1. Creating checkpoints...")
        agent._add_user_message("Message 1")
        checkpoint_manager.create("checkpoint-1", agent.get_history())

        agent._add_user_message("Message 2")
        checkpoint_manager.create("checkpoint-2", agent.get_history())

        agent._add_user_message("Message 3")
        checkpoint_manager.create("checkpoint-3", agent.get_history())

        # List checkpoints
        print("\n2. Available checkpoints:")
        for name in checkpoint_manager.list_checkpoints():
            print(f"   - {name}")


if __name__ == "__main__":
    example_basic_rewind()
    example_multiple_checkpoints()
    example_rewind_modes()
    example_error_handling()
    example_list_checkpoints()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
