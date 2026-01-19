"""Context awareness and collection."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from git import Repo, InvalidGitRepositoryError


class ExecutionContext:
    """Collect and manage execution context."""

    def __init__(self):
        """Initialize context collector."""
        self._context_cache: Optional[dict] = None
        self._cache_time: Optional[datetime] = None

    def get_context(self, force_refresh: bool = False) -> dict:
        """Get current execution context."""
        # Cache context for 30 seconds
        if not force_refresh and self._context_cache:
            if self._cache_time:
                age = datetime.now() - self._cache_time
                if age.total_seconds() < 30:
                    return self._context_cache

        # Collect fresh context
        context = {
            "working_dir": self._get_working_dir(),
            "git_branch": self._get_git_branch(),
            "git_repo": self._get_git_repo(),
            "hour_of_day": datetime.now().hour,
            "day_of_week": datetime.now().weekday(),
            "hostname": self._get_hostname(),
            "user": self._get_user(),
            "shell": self._get_shell(),
        }

        self._context_cache = context
        self._cache_time = datetime.now()

        return context

    def _get_working_dir(self) -> str:
        """Get current working directory."""
        return str(Path.cwd())

    def _get_git_branch(self) -> Optional[str]:
        """Get current git branch."""
        try:
            repo = Repo(os.getcwd(), search_parent_directories=True)
            try:
                return repo.active_branch.name
            except TypeError:
                # Detached HEAD
                return None
        except InvalidGitRepositoryError:
            return None

    def _get_git_repo(self) -> Optional[str]:
        """Get git repository name."""
        try:
            repo = Repo(os.getcwd(), search_parent_directories=True)
            return os.path.basename(repo.working_dir)
        except InvalidGitRepositoryError:
            return None

    def _get_hostname(self) -> str:
        """Get hostname."""
        import socket

        return socket.gethostname()

    def _get_user(self) -> str:
        """Get current username."""
        return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))

    def _get_shell(self) -> str:
        """Get current shell."""
        return os.environ.get("SHELL", "unknown")

    def is_in_git_repo(self) -> bool:
        """Check if current directory is in a git repository."""
        return self._get_git_branch() is not None

    def is_in_project(self, project_name: str) -> bool:
        """Check if current directory is in specific project."""
        git_repo = self._get_git_repo()
        return git_repo == project_name if git_repo else False

    def get_project_name(self) -> Optional[str]:
        """Try to identify the current project name."""
        # Try git repo name
        git_repo = self._get_git_repo()
        if git_repo:
            return git_repo

        # Try directory name
        return os.path.basename(os.getcwd())


class ContextAnalyzer:
    """Analyze context to provide insights."""

    def __init__(self):
        """Initialize context analyzer."""
        self.collector = ExecutionContext()

    def suggest_commands_for_context(self, context: dict) -> list[str]:
        """Suggest commands based on context."""
        suggestions = []

        # Git repo context
        if context.get("git_branch"):
            suggestions.extend(["git:status", "git:commit", "git:push"])

        # Project-specific suggestions could go here
        # For example, if in a Python project, suggest pytest, black, etc.

        return suggestions

    def get_routine_tasks(self, context: dict) -> list[str]:
        """Get routine tasks based on time context."""
        hour = context.get("hour_of_day", 0)
        day = context.get("day_of_week", 0)

        tasks = []

        # Morning routine
        if 8 <= hour < 10:
            tasks.extend(["email:check", "calendar:today", "news:read"])

        # End of day
        if 17 <= hour < 19:
            tasks.extend(["git:push", "work:save", "backup:create"])

        # Monday planning
        if day == 0 and 9 <= hour < 11:
            tasks.extend(["plan:week", "tasks:review"])

        return tasks
