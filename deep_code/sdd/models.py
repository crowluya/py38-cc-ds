"""
SDD (Spec-Driven Development) data models.

Defines the core data structures for tasks, phases, dependencies,
and task status following Python 3.8.10 compatibility requirements.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class TaskStatus(Enum):
    """Status of a task in the SDD workflow."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class Dependency:
    """
    Represents a dependency relationship between tasks.

    Attributes:
        task_id: The ID of the task this depends on
        type: Type of dependency ('after' or 'parallel')
    """

    task_id: str
    type: str = "after"

    def __eq__(self, other: object) -> bool:
        """Check equality based on task_id and type."""
        if not isinstance(other, Dependency):
            return NotImplemented
        return self.task_id == other.task_id and self.type == other.type


@dataclass
class Task:
    """
    Represents a single task in the SDD workflow.

    Attributes:
        id: Unique task identifier (e.g., "T001")
        description: Human-readable task description
        status: Current status of the task
        dependencies: List of tasks this task depends on
        parallel: Whether this task can be executed in parallel with others
        tdd: Whether this task follows TDD (test-first)
        file: Target file path for this task (optional)
        function: Target function name for this task (optional)
    """

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[Dependency] = field(default_factory=list)
    parallel: bool = False
    tdd: bool = True
    file: Optional[str] = None
    function: Optional[str] = None


@dataclass
class Phase:
    """
    Represents a phase in the SDD workflow.

    A phase groups related tasks together.

    Attributes:
        id: Unique phase identifier (e.g., "phase-a")
        name: Human-readable phase name
        description: Detailed description of the phase
        tasks: List of tasks in this phase
    """

    id: str
    name: str
    description: str
    tasks: List[Task] = field(default_factory=list)
