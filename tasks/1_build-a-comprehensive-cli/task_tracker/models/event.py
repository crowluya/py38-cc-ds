"""Event model for tracking task state changes."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class EventType(str, Enum):
    """Types of events that can occur."""
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"
    TIME_LOGGED = "time_logged"
    COMMENT_ADDED = "comment_added"


@dataclass
class Event:
    """
    Event model for tracking task state changes and history.

    Attributes:
        id: Unique event identifier
        task_id: Associated task ID
        event_type: Type of event
        timestamp: When the event occurred
        old_value: Previous value (for state changes)
        new_value: New value (for state changes)
        metadata: Additional event metadata
        user: User who triggered the event
    """
    id: Optional[int] = None
    task_id: Optional[int] = None
    event_type: EventType = EventType.CREATED
    timestamp: datetime = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    metadata: Dict[str, Any] = None
    user: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "metadata": self.metadata,
            "user": self.user,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        if isinstance(data.get("event_type"), str):
            data["event_type"] = EventType(data["event_type"])

        if data.get("timestamp") and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)
