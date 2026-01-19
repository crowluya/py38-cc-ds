"""ML-based recommendation engine."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from ai_command_palette.core.registry import Command, CommandType
from ai_command_palette.core.scorer import CommandScorer, ScoredCommand
from ai_command_palette.storage.config import Config
from ai_command_palette.storage.database import Database


class RecommendationEngine:
    """Intelligent recommendation engine."""

    def __init__(self, db: Database, scorer: CommandScorer, config: Optional[Config] = None):
        """Initialize recommendation engine."""
        self.db = db
        self.scorer = scorer
        self.config = config or Config()

    def get_suggestions(
        self,
        query: str,
        context: Optional[dict] = None,
        limit: int = 20,
        command_types: Optional[list[CommandType]] = None,
    ) -> list[ScoredCommand]:
        """Get intelligent suggestions based on query and context."""
        # Get all available commands
        # In a real implementation, this would come from a CommandRegistry
        # For now, we'll return an empty list
        return []

    def get_trending_commands(self, days: int = 7, limit: int = 10) -> list[tuple[str, int]]:
        """Get trending commands (rapidly increasing in popularity)."""
        session = self.db.get_session()
        try:
            from sqlalchemy import and_, func
            from ai_command_palette.storage.database import CommandUsage

            # Compare recent usage to baseline
            recent_days = 7
            baseline_days = 30

            recent_start = datetime.utcnow() - timedelta(days=recent_days)
            baseline_start = datetime.utcnow() - timedelta(days=baseline_days)

            # Recent usage
            recent_counts = (
                session.query(
                    CommandUsage.command, func.count(CommandUsage.id).label("count")
                )
                .filter(CommandUsage.timestamp >= recent_start)
                .group_by(CommandUsage.command)
                .subquery()
            )

            # Baseline usage
            baseline_counts = (
                session.query(
                    CommandUsage.command, func.count(CommandUsage.id).label("count")
                )
                .filter(
                    and_(
                        CommandUsage.timestamp >= baseline_start,
                        CommandUsage.timestamp < recent_start,
                    )
                )
                .group_by(CommandUsage.command)
                .subquery()
            )

            # Calculate trend (recent rate / baseline rate)
            # This is simplified - a real implementation would be more sophisticated
            # For now, just return most frequent recent commands

            trending = (
                session.query(
                    CommandUsage.command, func.count(CommandUsage.id).label("count")
                )
                .filter(CommandUsage.timestamp >= recent_start)
                .group_by(CommandUsage.command)
                .order_by(func.count(CommandUsage.id).desc())
                .limit(limit)
                .all()
            )

            return [(cmd, count) for cmd, count in trending]

        finally:
            session.close()

    def get_contextual_suggestions(
        self, context: dict, limit: int = 10
    ) -> list[ScoredCommand]:
        """Get suggestions based purely on context."""
        # This would use the context to suggest relevant commands
        # For example:
        # - In a git repo: suggest git commands
        # - In a Python project: suggest python-related commands
        # - At certain times: suggest routine tasks

        suggestions = []

        # Git context
        if context.get("git_branch"):
            # Suggest git commands
            pass

        # Directory context
        if context.get("working_dir"):
            # Suggest project-specific commands
            pass

        # Time context
        hour = context.get("hour_of_day")
        if hour:
            # Suggest routine tasks for this time
            pass

        return suggestions


class PatternLearner:
    """Learn patterns from usage data."""

    def __init__(self, db: Database):
        """Initialize pattern learner."""
        self.db = db

    def learn_time_patterns(self) -> dict[str, dict]:
        """Learn time-based usage patterns."""
        session = self.db.get_session()
        try:
            from sqlalchemy import extract, func
            from ai_command_palette.storage.database import CommandUsage

            # Get commands by hour of day
            hourly_commands = (
                session.query(
                    extract("hour", CommandUsage.timestamp).label("hour"),
                    CommandUsage.command,
                    func.count(CommandUsage.id).label("count"),
                )
                .group_by("hour", CommandUsage.command)
                .all()
            )

            # Organize by hour
            patterns: dict[int, dict[str, int]] = defaultdict(dict)
            for hour, command, count in hourly_commands:
                patterns[int(hour)][command] = count

            return {str(k): v for k, v in patterns.items()}

        finally:
            session.close()

    def learn_sequence_patterns(self) -> dict[str, list[str]]:
        """Learn command sequences (commands frequently used together)."""
        session = self.db.get_session()
        try:
            from sqlalchemy import and_
            from ai_command_palette.storage.database import CommandUsage

            # Get all command usage ordered by time
            usages = (
                session.query(CommandUsage)
                .order_by(CommandUsage.timestamp)
                .limit(10000)
                .all()
            )

            # Find sequences (commands executed within 5 minutes of each other)
            sequences: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

            for i, usage in enumerate(usages[:-1]):
                next_usage = usages[i + 1]

                # Check if next command is within time window
                time_diff = next_usage.timestamp - usage.timestamp
                if time_diff < timedelta(minutes=5):
                    sequences[usage.command][next_usage.command] += 1

            # Get top sequences for each command
            top_sequences: dict[str, list[str]] = {}
            for cmd, followers in sequences.items():
                sorted_followers = sorted(
                    followers.items(), key=lambda x: x[1], reverse=True
                )
                top_sequences[cmd] = [f for f, _ in sorted_followers[:3]]

            return top_sequences

        finally:
            session.close()

    def learn_directory_patterns(self) -> dict[str, list[str]]:
        """Learn which commands are commonly used in which directories."""
        session = self.db.get_session()
        try:
            from sqlalchemy import func
            from ai_command_palette.storage.database import CommandUsage

            # Group by working directory
            dir_commands = (
                session.query(
                    CommandUsage.working_dir,
                    CommandUsage.command,
                    func.count(CommandUsage.id).label("count"),
                )
                .filter(CommandUsage.working_dir is not None)
                .group_by(CommandUsage.working_dir, CommandUsage.command)
                .all()
            )

            # Organize by directory
            patterns: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
            for working_dir, command, count in dir_commands:
                patterns[working_dir][command] = count

            # Get top commands for each directory
            top_patterns: dict[str, list[str]] = {}
            for dir, commands in patterns.items():
                sorted_commands = sorted(commands.items(), key=lambda x: x[1], reverse=True)
                top_patterns[dir] = [c for c, _ in sorted_commands[:5]]

            return top_patterns

        finally:
            session.close()
