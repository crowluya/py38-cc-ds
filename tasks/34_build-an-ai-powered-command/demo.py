#!/usr/bin/env python3
"""Demo script for AI Command Palette."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_command_palette.core.registry import CommandRegistry, CommandType
from ai_command_palette.core.scorer import CommandScorer
from ai_command_palette.storage.config import Config
from ai_command_palette.storage.database import Database
from ai_command_palette.core.tracker import UsageTracker


def demo_registry():
    """Demonstrate command registry."""
    print("=" * 60)
    print("Command Registry Demo")
    print("=" * 60)

    registry = CommandRegistry()
    registry.initialize()

    print(f"\n✓ Registered {len(registry.get_all())} commands")

    # List some commands
    print("\nSample Commands:")
    for cmd in registry.get_all()[:5]:
        print(f"  • {cmd.name}: {cmd.description}")

    # Search commands
    print("\nSearching for 'git':")
    results = registry.search("git")
    for cmd in results:
        print(f"  • {cmd.name}: {cmd.description}")


def demo_scoring():
    """Demonstrate command scoring."""
    print("\n" + "=" * 60)
    print("Command Scoring Demo")
    print("=" * 60)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config()
        config.data_dir = tmpdir
        db = Database(config)

        # Create scorer
        scorer = CommandScorer(db)

        # Create test commands
        from ai_command_palette.core.registry import Command

        commands = [
            Command(
                name="git:status",
                command_type=CommandType.SYSTEM,
                command_template="git status",
                description="Show git status",
                category="Git",
            ),
            Command(
                name="git:commit",
                command_type=CommandType.SYSTEM,
                command_template="git commit",
                description="Commit changes",
                category="Git",
            ),
            Command(
                name="note:create",
                command_type=CommandType.NOTE,
                command_template="note create",
                description="Create a note",
                category="Notes",
            ),
        ]

        # Score commands
        print("\nScoring commands for query 'git':")
        scored = scorer.score_commands(commands, "git", context={"git_branch": "main"})

        for i, scored_cmd in enumerate(scored[:5], 1):
            details = scored_cmd.match_details
            print(
                f"  {i}. {scored_cmd.command.name} "
                f"(score: {scored_cmd.score:.2f})"
            )
            print(f"     Fuzzy: {details['fuzzy']:.2f}, "
                  f"Frequency: {details['frequency']:.2f}, "
                  f"Recency: {details['recency']:.2f}")


def demo_tracking():
    """Demonstrate usage tracking."""
    print("\n" + "=" * 60)
    print("Usage Tracking Demo")
    print("=" * 60)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config()
        config.data_dir = tmpdir
        db = Database(config)

        tracker = UsageTracker(db)

        # Track some commands
        print("\nTracking commands...")

        commands_to_track = [
            ("git status", "system"),
            ("note create test", "note"),
            ("git commit", "system"),
            ("git status", "system"),
            ("pytest", "system"),
        ]

        for cmd, cmd_type in commands_to_track:
            tracker.track_command(command=cmd, command_type=cmd_type)
            print(f"  ✓ Tracked: {cmd}")

        # Get statistics
        print("\nCommand frequency:")
        freq = tracker.get_frequent_commands(limit=5, days=30)
        for cmd, count in freq:
            print(f"  • {cmd}: {count}x")

        # Get recent commands
        print("\nRecent commands:")
        recent = tracker.get_recent_commands(limit=5)
        for usage in recent:
            print(f"  • {usage.command} ({usage.timestamp.strftime('%H:%M:%S')})")


def demo_config():
    """Demonstrate configuration."""
    print("\n" + "=" * 60)
    print("Configuration Demo")
    print("=" * 60)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config()
        config.config_dir = tmpdir
        config.data_dir = tmpdir

        print("\nDefault configuration:")
        print(f"  Config dir: {config.config_dir}")
        print(f"  Data dir: {config.data_dir}")
        print(f"  Learning enabled: {config.learning.enabled}")
        print(f"  Retention days: {config.learning.retention_days}")
        print(f"  Max results: {config.ui.max_results}")

        # Save and load
        config.save()
        print(f"\n✓ Configuration saved to {config.config_dir / 'config.json'}")

        # Load new instance
        config2 = Config()
        config2.config_dir = tmpdir
        config2.data_dir = tmpdir
        config2._load_from_file(tmpdir / "config.json")

        print(f"✓ Configuration loaded successfully")


def main():
    """Run all demos."""
    print("\n🚀 AI Command Palette Demo\n")

    try:
        demo_registry()
        demo_scoring()
        demo_tracking()
        demo_config()

        print("\n" + "=" * 60)
        print("✓ Demo completed successfully!")
        print("=" * 60)

        print("\nTo use AI Command Palette:")
        print("  1. Install: pip install -e .")
        print("  2. Initialize: aicp init")
        print("  3. Launch: aicp launch")
        print("\nFor more examples, see EXAMPLES.md")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
