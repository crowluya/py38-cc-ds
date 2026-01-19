"""Task model with all task-related data structures."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    """
    Task model representing a workspace task.

    Attributes:
        id: Unique task identifier
        title: Task title/name
        description: Detailed task description
        status: Current task status
        priority: Task priority level
        tags: List of tags for categorization
        created_at: Task creation timestamp
        updated_at: Last update timestamp
        started_at: Task start timestamp (when work began)
        completed_at: Task completion timestamp
        estimated_time: Estimated time in minutes
        actual_time: Actual time spent in minutes
        metadata: Additional task metadata
        parent_id: Parent task ID for subtasks
        project: Project name/category
        assignee: Task assignee
    """
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_time: Optional[int] = None  # in minutes
    actual_time: int = 0  # in minutes
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[int] = None
    project: Optional[str] = None
    assignee: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "priority": self.priority.value if isinstance(self.priority, TaskPriority) else self.priority,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_time": self.estimated_time,
            "actual_time": self.actual_time,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "project": self.project,
            "assignee": self.assignee,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary."""
        if isinstance(data.get("status"), str):
            data["status"] = TaskStatus(data["status"])
        if isinstance(data.get("priority"), str):
            data["priority"] = TaskPriority(data["priority"])

        # Convert ISO strings back to datetime objects
        for field_name in ["created_at", "updated_at", "started_at", "completed_at"]:
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])

        return cls(**data)

    @property
    def duration(self) -> Optional[int]:
        """Calculate total duration in minutes."""
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at).total_seconds() / 60)
        return None

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue based on estimated time."""
        if self.estimated_time and self.actual_time > self.estimated_time:
            return True
        return False

    @property
    def age_in_hours(self) -> float:
        """Calculate task age in hours since creation."""
        return (datetime.now() - self.created_at).total_seconds() / 3600
