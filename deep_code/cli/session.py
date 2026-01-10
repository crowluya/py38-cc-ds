"""
Session Management (CMD-001 to CMD-004)

Python 3.8.10 compatible
Provides session persistence for conversation history.
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class TokenStats:
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, prompt: int, completion: int) -> None:
        """Add token counts."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenStats":
        """Create from dictionary."""
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )


@dataclass
class Session:
    """A conversation session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    messages: List[Message] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    stats: TokenStats = field(default_factory=TokenStats)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session."""
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.now().isoformat()

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message."""
        self.add_message("assistant", content)

    def add_tokens(self, prompt: int, completion: int) -> None:
        """Add token usage."""
        self.stats.add(prompt, completion)
        self.updated_at = datetime.now().isoformat()

    def get_messages_for_context(self) -> List[Dict[str, str]]:
        """Get messages in format suitable for LLM context."""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "context": self.context,
            "stats": self.stats.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from dictionary."""
        messages = [Message.from_dict(m) for m in data.get("messages", [])]
        stats = TokenStats.from_dict(data.get("stats", {}))
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            messages=messages,
            context=data.get("context", {}),
            stats=stats,
        )


class SessionStore:
    """
    Persistent storage for sessions.

    Stores sessions as JSON files in .deepcode/sessions/
    """

    def __init__(self, project_root: Optional[str] = None) -> None:
        """
        Initialize session store.

        Args:
            project_root: Project root directory. If None, uses current directory.
        """
        if project_root:
            self._root = Path(project_root)
        else:
            self._root = Path.cwd()

        self._sessions_dir = self._root / ".deepcode" / "sessions"
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure sessions directory exists."""
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        """Get path for a session file."""
        return self._sessions_dir / f"{session_id}.json"

    def save(self, session: Session) -> None:
        """
        Save a session to disk.

        Args:
            session: Session to save
        """
        path = self._session_path(session.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)

    def load(self, session_id: str) -> Optional[Session]:
        """
        Load a session from disk.

        Args:
            session_id: Session ID to load

        Returns:
            Session if found, None otherwise
        """
        path = self._session_path(session_id)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Session.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return None

    def delete(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(self, limit: int = 20) -> List[Session]:
        """
        List recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of sessions, sorted by updated_at descending
        """
        sessions = []

        for path in self._sessions_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(Session.from_dict(data))
            except (json.JSONDecodeError, IOError):
                continue

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        return sessions[:limit]

    def get_latest(self) -> Optional[Session]:
        """
        Get the most recently updated session.

        Returns:
            Latest session or None if no sessions exist
        """
        sessions = self.list_sessions(limit=1)
        return sessions[0] if sessions else None

    def cleanup_old(self, days: int = 7) -> int:
        """
        Delete sessions older than specified days.

        Args:
            days: Delete sessions older than this many days

        Returns:
            Number of sessions deleted
        """
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        deleted = 0

        for path in self._sessions_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                updated_at = data.get("updated_at", "")
                if updated_at < cutoff_str:
                    path.unlink()
                    deleted += 1
            except (json.JSONDecodeError, IOError):
                continue

        return deleted


# Convenience functions

def create_session(project_root: Optional[str] = None, mode: str = "default") -> Session:
    """
    Create a new session.

    Args:
        project_root: Project root directory
        mode: Execution mode

    Returns:
        New session
    """
    session = Session()
    session.context = {
        "project_root": project_root or str(Path.cwd()),
        "mode": mode,
    }
    return session


def save_session(session: Session, project_root: Optional[str] = None) -> None:
    """
    Save a session.

    Args:
        session: Session to save
        project_root: Project root directory
    """
    store = SessionStore(project_root)
    store.save(session)


def load_session(session_id: str, project_root: Optional[str] = None) -> Optional[Session]:
    """
    Load a session by ID.

    Args:
        session_id: Session ID
        project_root: Project root directory

    Returns:
        Session if found
    """
    store = SessionStore(project_root)
    return store.load(session_id)


def get_latest_session(project_root: Optional[str] = None) -> Optional[Session]:
    """
    Get the most recent session.

    Args:
        project_root: Project root directory

    Returns:
        Latest session if exists
    """
    store = SessionStore(project_root)
    return store.get_latest()


def list_sessions(project_root: Optional[str] = None, limit: int = 20) -> List[Session]:
    """
    List recent sessions.

    Args:
        project_root: Project root directory
        limit: Maximum sessions to return

    Returns:
        List of sessions
    """
    store = SessionStore(project_root)
    return store.list_sessions(limit)
