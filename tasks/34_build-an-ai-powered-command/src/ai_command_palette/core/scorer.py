"""Scoring and ranking engine for recommendations."""

import math
from datetime import datetime, timedelta
from typing import Optional

from rapidfuzz import fuzz, process

from ai_command_palette.core.registry import Command
from ai_command_palette.storage.config import Config
from ai_command_palette.storage.database import Database


class ScoredCommand:
    """Command with associated score."""

    def __init__(
        self,
        command: Command,
        score: float,
        match_details: Optional[dict] = None,
    ):
        """Initialize scored command."""
        self.command = command
        self.score = score
        self.match_details = match_details or {}

    def __lt__(self, other: "ScoredCommand") -> bool:
        """Compare for sorting (higher scores first)."""
        return self.score > other.score

    def __repr__(self) -> str:
        """String representation."""
        return f"ScoredCommand({self.command.name}, score={self.score:.2f})"


class CommandScorer:
    """Score and rank command suggestions."""

    def __init__(self, db: Database, config: Optional[Config] = None):
        """Initialize scorer."""
        self.db = db
        self.config = config or Config()

        # Get scoring weights from config
        self.weights = {
            "frequency": self.config.scoring.frequency,
            "recency": self.config.scoring.recency,
            "fuzzy_match": self.config.scoring.fuzzy_match,
            "context_boost": self.config.scoring.context_boost,
        }

        # Cache for command statistics
        self._frequency_cache: dict[str, int] = {}
        self._last_used_cache: dict[str, datetime] = {}
        self._cache_timestamp: Optional[datetime] = None

    def score_commands(
        self,
        commands: list[Command],
        query: str,
        context: Optional[dict] = None,
    ) -> list[ScoredCommand]:
        """Score and rank a list of commands."""
        # Update cache if needed
        self._update_cache()

        scored = []
        for cmd in commands:
            score = self.score_command(cmd, query, context)
            scored.append(score)

        # Sort by score (descending)
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    def score_command(
        self,
        command: Command,
        query: str,
        context: Optional[dict] = None,
    ) -> ScoredCommand:
        """Score a single command."""
        # Fuzzy match score
        fuzzy_score = self._fuzzy_match(command.name, query)

        # Frequency score
        freq_score = self._frequency_score(command.name)

        # Recency score
        recency_score = self._recency_score(command.name)

        # Context boost
        context_score = self._context_boost(command, context)

        # Calculate weighted score
        total_score = (
            self.weights["fuzzy_match"] * fuzzy_score
            + self.weights["frequency"] * freq_score
            + self.weights["recency"] * recency_score
            + self.weights["context_boost"] * context_score
        )

        # Create match details
        match_details = {
            "fuzzy": fuzzy_score,
            "frequency": freq_score,
            "recency": recency_score,
            "context": context_score,
        }

        return ScoredCommand(command, total_score, match_details)

    def _fuzzy_match(self, command_name: str, query: str) -> float:
        """Calculate fuzzy match score (0-100)."""
        if not query:
            return 50.0  # Neutral score if no query

        # Use rapidfuzz for fast fuzzy matching
        ratio = fuzz.partial_ratio(command_name.lower(), query.lower())

        # Normalize to 0-1
        return ratio / 100.0

    def _frequency_score(self, command_name: str) -> float:
        """Calculate frequency-based score."""
        freq = self._frequency_cache.get(command_name, 0)

        if freq == 0:
            return 0.0

        # Use logarithmic scale to prevent very frequent commands
        # from dominating completely
        return math.log(freq + 1) / 10.0

    def _recency_score(self, command_name: str) -> float:
        """Calculate recency-based score."""
        last_used = self._last_used_cache.get(command_name)

        if not last_used:
            return 0.0

        # Calculate time difference
        time_diff = (datetime.now() - last_used).total_seconds()

        # Exponential decay: more recent = higher score
        # Score decays over time (half-life of 7 days)
        half_life = 7 * 24 * 3600  # 7 days in seconds
        decay = math.exp(-time_diff / half_life)

        return decay

    def _context_boost(self, command: Command, context: Optional[dict]) -> float:
        """Calculate context-based boost."""
        if not context:
            return 0.0

        boost = 0.0

        # Directory context boost
        if "working_dir" in context:
            working_dir = context["working_dir"]

            # Boost file commands in current directory
            if command.command_type.value == "file" and working_dir:
                if working_dir in command.command_template:
                    boost += 0.3

        # Git branch context
        if "git_branch" in context and context["git_branch"]:
            # Boost git-related commands when in a git repo
            if command.category == "Git":
                boost += 0.5

        # Time-based context
        if "hour_of_day" in context:
            hour = context["hour_of_day"]

            # Boost "deploy" commands during business hours
            if "deploy" in command.name.lower() and 9 <= hour <= 17:
                boost += 0.2

        return min(boost, 1.0)  # Cap at 1.0

    def _update_cache(self):
        """Update cached statistics from database."""
        # Refresh cache every 5 minutes
        if self._cache_timestamp:
            age = datetime.now() - self._cache_timestamp
            if age < timedelta(minutes=5):
                return

        # Get frequency data
        freq_data = self.db.get_command_frequency(days=30)
        self._frequency_cache = freq_data

        # Get recent command data for recency
        recent = self.db.get_recent_commands(limit=1000)
        self._last_used_cache = {}
        for usage in recent:
            if usage.command not in self._last_used_cache:
                self._last_used_cache[usage.command] = usage.timestamp

        self._cache_timestamp = datetime.now()

    def get_top_commands(
        self,
        command_type: Optional[str] = None,
        limit: int = 10,
        days: int = 30,
    ) -> list[tuple[str, int]]:
        """Get top commands by frequency."""
        return self.db.get_command_frequency(command_type=command_type, days=days)[:limit]

    def get_related_commands(self, command_name: str, limit: int = 5) -> list[str]:
        """Get commands frequently used together with given command."""
        # This is a simple implementation based on command sequences
        # A more advanced version would use association rule mining

        session = self.db.get_session()
        try:
            from sqlalchemy import and_
            from ai_command_palette.storage.database import CommandUsage

            # Find commands executed within 5 minutes of the given command
            target_usages = (
                session.query(CommandUsage)
                .filter(CommandUsage.command == command_name)
                .all()
            )

            related_counts: dict[str, int] = {}

            for usage in target_usages:
                # Look for commands within 5 minutes before or after
                time_window = timedelta(minutes=5)
                start_time = usage.timestamp - time_window
                end_time = usage.timestamp + time_window

                nearby = (
                    session.query(CommandUsage)
                    .filter(
                        and_(
                            CommandUsage.timestamp >= start_time,
                            CommandUsage.timestamp <= end_time,
                            CommandUsage.id != usage.id,
                            CommandUsage.command != command_name,
                        )
                    )
                    .all()
                )

                for nearby_usage in nearby:
                    cmd = nearby_usage.command
                    related_counts[cmd] = related_counts.get(cmd, 0) + 1

            # Sort by frequency
            related = sorted(related_counts.items(), key=lambda x: x[1], reverse=True)
            return [cmd for cmd, _ in related[:limit]]

        finally:
            session.close()
