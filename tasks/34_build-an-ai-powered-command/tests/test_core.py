"""Unit tests for core components."""

import pytest
from datetime import datetime, timedelta

from ai_command_palette.core.registry import Command, CommandRegistry, CommandType
from ai_command_palette.core.scorer import CommandScorer, ScoredCommand
from ai_command_palette.storage.config import Config
from ai_command_palette.storage.database import Database


class TestCommandRegistry:
    """Test command registry functionality."""

    def test_register_command(self):
        """Test registering a single command."""
        registry = CommandRegistry()
        cmd = Command(
            name="test:command",
            command_type=CommandType.SYSTEM,
            description="Test command",
            command_template="echo 'test'",
        )

        registry.register(cmd)

        assert registry.get("test:command") == cmd
        assert len(registry.get_all()) == 1

    def test_register_multiple_commands(self):
        """Test registering multiple commands."""
        registry = CommandRegistry()
        commands = [
            Command(
                name=f"test:cmd{i}",
                command_type=CommandType.SYSTEM,
                description=f"Command {i}",
                command_template=f"echo 'test{i}'",
            )
            for i in range(5)
        ]

        registry.register_commands(commands)

        assert len(registry.get_all()) == 5

    def test_search_commands(self):
        """Test searching commands."""
        registry = CommandRegistry()
        registry.register(
            Command(
                name="git:commit",
                command_type=CommandType.SYSTEM,
                description="Commit changes",
                command_template="git commit",
                category="Git",
                tags=["git", "commit"],
            )
        )

        results = registry.search("git")
        assert len(results) == 1
        assert results[0].name == "git:commit"

        results = registry.search("commit")
        assert len(results) == 1

    def test_get_by_category(self):
        """Test getting commands by category."""
        registry = CommandRegistry()
        registry.register(
            Command(
                name="git:status",
                command_type=CommandType.SYSTEM,
                command_template="git status",
                category="Git",
            )
        )
        registry.register(
            Command(
                name="note:create",
                command_type=CommandType.NOTE,
                command_template="note create",
                category="Notes",
            )
        )

        git_commands = registry.get_by_category("Git")
        assert len(git_commands) == 1
        assert git_commands[0].name == "git:status"

    def test_get_by_type(self):
        """Test getting commands by type."""
        registry = CommandRegistry()
        registry.register(
            Command(
                name="git:status",
                command_type=CommandType.SYSTEM,
                command_template="git status",
            )
        )
        registry.register(
            Command(
                name="note:create",
                command_type=CommandType.NOTE,
                command_template="note create",
            )
        )

        system_commands = registry.get_by_type(CommandType.SYSTEM)
        assert len(system_commands) == 1
        assert system_commands[0].command_type == CommandType.SYSTEM


class TestCommandScorer:
    """Test command scoring functionality."""

    @pytest.fixture
    def db(self):
        """Create test database."""
        # Use in-memory database for tests
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.data_dir = tmpdir
            yield Database(config)

    @pytest.fixture
    def scorer(self, db):
        """Create scorer with test database."""
        return CommandScorer(db)

    def test_fuzzy_match(self, scorer):
        """Test fuzzy matching."""
        score = scorer._fuzzy_match("git:status", "git")
        assert score > 0.5  # Should have good match

        score = scorer._fuzzy_match("git:status", "note")
        assert score < 0.5  # Should have poor match

    def test_score_command(self, scorer):
        """Test scoring a single command."""
        cmd = Command(
            name="git:status",
            command_type=CommandType.SYSTEM,
            command_template="git status",
        )

        scored = scorer.score_command(cmd, "git")

        assert isinstance(scored, ScoredCommand)
        assert scored.command == cmd
        assert 0 <= scored.score <= 1

    def test_score_commands(self, scorer):
        """Test scoring multiple commands."""
        commands = [
            Command(name="git:status", command_type=CommandType.SYSTEM, command_template="git status"),
            Command(name="git:commit", command_type=CommandType.SYSTEM, command_template="git commit"),
            Command(name="note:create", command_type=CommandType.NOTE, command_template="note create"),
        ]

        scored = scorer.score_commands(commands, "git")

        assert len(scored) == 3
        assert isinstance(scored[0], ScoredCommand)
        # Git commands should rank higher
        git_commands = [s for s in scored if "git" in s.command.name]
        assert len(git_commands) == 2

    def test_context_boost(self, scorer):
        """Test context-based scoring boost."""
        cmd = Command(
            name="git:status",
            command_type=CommandType.SYSTEM,
            command_template="git status",
            category="Git",
        )

        # Test with git context
        context = {"git_branch": "main"}
        score_git = scorer._context_boost(cmd, context)

        # Test without git context
        score_no_git = scorer._context_boost(cmd, {})

        assert score_git > score_no_git


class TestConfig:
    """Test configuration management."""

    def test_default_config(self):
        """Test default configuration."""
        config = Config()

        assert config.learning.enabled is True
        assert config.learning.retention_days == 90
        assert config.scoring.frequency == 0.4
        assert config.ui.max_results == 20

    def test_config_save_load(self, tmp_path):
        """Test saving and loading configuration."""
        config = Config()
        config.config_dir = tmp_path
        config.data_dir = tmp_path

        # Modify some values
        config.learning.retention_days = 60
        config.ui.max_results = 30

        # Save
        config.save()

        # Load new instance
        config2 = Config()
        config2.config_dir = tmp_path
        config2.data_dir = tmp_path
        config2._load_from_file(tmp_path / "config.json")

        assert config2.learning.retention_days == 60
        assert config2.ui.max_results == 30


@pytest.mark.integration
class TestDatabase:
    """Integration tests for database."""

    def test_log_command(self):
        """Test logging a command."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.data_dir = tmpdir
            db = Database(config)

            usage = db.log_command(
                command="git status",
                command_type="system",
                working_dir="/home/user/project",
                exit_code=0,
            )

            assert usage.command == "git status"
            assert usage.command_type == "system"
            assert usage.success is True

    def test_get_command_frequency(self):
        """Test getting command frequency statistics."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.data_dir = tmpdir
            db = Database(config)

            # Log some commands
            for _ in range(5):
                db.log_command(command="git status", command_type="system")
            for _ in range(3):
                db.log_command(command="note create", command_type="note")

            freq = db.get_command_frequency()

            assert freq["git status"] == 5
            assert freq["note create"] == 3
