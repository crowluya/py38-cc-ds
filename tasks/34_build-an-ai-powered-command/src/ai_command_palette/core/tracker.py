"""Usage tracking and analytics engine."""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from git import Repo, InvalidGitRepositoryError

from ai_command_palette.storage.database import Database


class UsageTracker:
    """Track and analyze command usage patterns."""

    def __init__(self, db: Optional[Database] = None):
        """Initialize usage tracker."""
        self.db = db or Database()

    def track_command(
        self,
        command: str,
        command_type: str = "system",
        args: Optional[str] = None,
        working_dir: Optional[str] = None,
        exit_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ):
        """Track a command execution."""
        # Get context information
        git_branch = self._get_git_branch(working_dir) if working_dir else None

        # Determine success
        success = exit_code is None or exit_code == 0

        # Log to database
        self.db.log_command(
            command=command,
            command_type=command_type,
            args=args,
            exit_code=exit_code,
            duration_ms=duration_ms,
            working_dir=working_dir,
            git_branch=git_branch,
            success=success,
        )

    def track_file_access(
        self,
        file_path: str,
        action: str,
        working_dir: Optional[str] = None,
    ):
        """Track a file access event."""
        # Determine file type
        file_type = self._get_file_type(file_path)

        # Log to database
        self.db.log_file_access(
            file_path=file_path,
            action=action,
            working_dir=working_dir,
            file_type=file_type,
        )

    def track_feedback(self, suggestion: str, accepted: bool, position: Optional[int] = None):
        """Track user feedback on suggestions."""
        self.db.log_feedback(suggestion=suggestion, accepted=accepted, position=position)

    def get_git_branch(self, working_dir: Optional[str] = None) -> Optional[str]:
        """Get current git branch for context."""
        return self._get_git_branch(working_dir)

    def _get_git_branch(self, working_dir: Optional[str] = None) -> Optional[str]:
        """Get git branch from working directory."""
        if not working_dir:
            working_dir = str(Path.cwd())

        try:
            repo = Repo(working_dir, search_parent_directories=True)
            try:
                return repo.active_branch.name
            except TypeError:
                # Detached HEAD state
                return None
        except InvalidGitRepositoryError:
            return None

    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from extension."""
        path = Path(file_path)
        ext = path.suffix.lower()

        # Common file type mappings
        type_map = {
            # Code
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            # Config
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".xml": "xml",
            # Docs
            ".md": "markdown",
            ".txt": "text",
            ".rst": "rst",
            # Other
            ".pdf": "pdf",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".gif": "image",
        }

        return type_map.get(ext, "unknown")

    def command_context(self) -> dict:
        """Get current execution context."""
        working_dir = str(Path.cwd())
        git_branch = self._get_git_branch(working_dir)
        hour_of_day = datetime.now().hour
        day_of_week = datetime.now().weekday()

        return {
            "working_dir": working_dir,
            "git_branch": git_branch,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
        }

    def get_frequent_commands(
        self, command_type: Optional[str] = None, limit: int = 20, days: int = 30
    ) -> list[tuple[str, int]]:
        """Get most frequently used commands."""
        freq = self.db.get_command_frequency(command_type=command_type, days=days)
        return list(sorted(freq.items(), key=lambda x: x[1], reverse=True))[:limit]

    def get_recent_commands(self, limit: int = 50) -> list:
        """Get recently executed commands."""
        return self.db.get_recent_commands(limit=limit)


class CommandTracker:
    """Context manager for tracking command execution."""

    def __init__(self, tracker: UsageTracker, command: str, command_type: str = "system"):
        """Initialize command tracker."""
        self.tracker = tracker
        self.command = command
        self.command_type = command_type
        self.start_time = None
        self.working_dir = str(Path.cwd())

    def __enter__(self):
        """Start tracking."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking and record execution."""
        duration_ms = int((time.time() - self.start_time) * 1000) if self.start_time else None

        # Determine exit code
        exit_code = 0 if exc_type is None else 1

        # Track the command
        self.tracker.track_command(
            command=self.command,
            command_type=self.command_type,
            working_dir=self.working_dir,
            exit_code=exit_code,
            duration_ms=duration_ms,
        )

        return False  # Don't suppress exceptions
