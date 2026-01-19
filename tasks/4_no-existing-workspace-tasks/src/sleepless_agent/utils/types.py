"""Type definitions for sleepless-agent.

This module provides comprehensive type hints for the entire codebase,
improving type safety and IDE support.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)

# Type aliases for common types
TaskID = int
ProjectID = str
TaskDescription = str
Timestamp = datetime
JSONDict = Dict[str, Any]

# Generic type variables
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class TaskStatus(str, Enum):
    """Status of a task in the queue."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""

    THOUGHT = "thought"
    SERIOUS = "serious"
    GENERATED = "generated"
    URGENT = "urgent"


class TaskType(str, Enum):
    """Type of task execution."""

    NEW = "new"
    REFINE = "refine"
    GENERAL = "general"


class AgentPhase(str, Enum):
    """Multi-agent workflow phases."""

    PLANNER = "planner"
    WORKER = "worker"
    EVALUATOR = "evaluator"


class ExitCode(int, Enum):
    """Task execution exit codes."""

    SUCCESS = 0
    ERROR = 1
    TIMEOUT = 124
    CANCELLED = 130


# TypedDicts for structured data
@dataclass(frozen=True)
class UsageMetrics:
    """Usage metrics from Claude execution."""

    total_cost_usd: float
    duration_ms: int
    duration_api_ms: int
    num_turns: int
    planner_cost_usd: Optional[float] = None
    planner_duration_ms: Optional[int] = None
    planner_turns: Optional[int] = None
    worker_cost_usd: Optional[float] = None
    worker_duration_ms: Optional[int] = None
    worker_turns: Optional[int] = None
    evaluator_cost_usd: Optional[float] = None
    evaluator_duration_ms: Optional[int] = None
    evaluator_turns: Optional[int] = None


@dataclass
class TaskContext:
    """Context information for a task."""

    task_id: TaskID
    description: TaskDescription
    priority: TaskPriority
    project_id: Optional[ProjectID] = None
    project_name: Optional[str] = None
    task_type: Optional[TaskType] = None
    refines_task_id: Optional[TaskID] = None
    generated_by: Optional[str] = None
    generated_at: Optional[Timestamp] = None


@dataclass
class ExecutionResult:
    """Result of task execution."""

    output_text: str
    files_modified: List[str]
    commands_executed: List[str]
    exit_code: ExitCode
    usage_metrics: UsageMetrics
    eval_status: Optional[str] = None
    eval_outstanding: Optional[List[str]] = None
    eval_recommendations: Optional[List[str]] = None


@dataclass
class WorkspaceInfo:
    """Information about a workspace."""

    path: Path
    task_id: Optional[TaskID] = None
    project_id: Optional[ProjectID] = None
    workspace_type: Literal["task", "project"] = "task"
    exists: bool = True


@dataclass
class GenerationContext:
    """Context for auto-generated tasks."""

    task_count: int
    pending_count: int
    in_progress_count: int
    mode: str
    recent_work: str
    available_tasks: str


# Function type aliases
AsyncQueryFunc = Callable[[str, Any], Iterator[Any]]
TaskProcessor = Callable[[TaskContext], ExecutionResult]
WorkspaceInitializer = Callable[[TaskID, TaskDescription], Path]
UsageChecker = Callable[[], Tuple[float, Optional[Timestamp]]]

# Dictionary types
ConfigDict = Dict[str, Any]
TaskDict = Dict[str, Union[str, int, float, bool, None]]
WorkspaceMapping = Dict[TaskID, Path]
