"""
SDD (Spec-Driven Development) Task Executor

Implements T114: Task executor with sequential and parallel execution.
Executes tasks in dependency order with support for parallel marked tasks [P].

Features:
- Task data model for execution
- Task parsing from tasks.md format
- Dependency analysis (topological sort)
- Sequential task execution
- Parallel task execution for [P] marked tasks
- Agent integration for code generation
- Task status and result tracking

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ===== Task Data Model =====


class TaskStatus(Enum):
    """Status of a task during execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """
    Represents a single task in the SDD workflow.

    Attributes:
        id: Unique task identifier (e.g., "T001")
        description: Human-readable task description
        status: Current status of the task
        phase: Phase identifier (optional)
        dependencies: List of task IDs this task depends on
        parallel: Whether this task can be executed in parallel with others
        tdd: Whether this task follows TDD (test-first)
        file: Target file path for this task (optional)
        function: Target function name for this task (optional)
    """

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    phase: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    parallel: bool = False
    tdd: bool = True
    file: Optional[str] = None
    function: Optional[str] = None

    def __str__(self) -> str:
        """String representation."""
        parallel_mark = " [P]" if self.parallel else ""
        return f"{self.id}: {self.description}{parallel_mark}"


@dataclass
class TaskResult:
    """
    Result of task execution.

    Attributes:
        task_id: ID of the executed task
        success: Whether the task completed successfully
        output: Output from task execution
        error: Error message if task failed
        execution_time: Time taken to execute (seconds)
        start_time: Task start timestamp
        end_time: Task end timestamp
    """

    task_id: str
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0


# ===== Exceptions =====


class TaskExecutionError(Exception):
    """Base exception for task execution errors."""

    pass


class CircularDependencyError(TaskExecutionError):
    """Raised when circular dependencies are detected."""

    def __init__(self, cycle: List[str]):
        """Initialize with cycle information."""
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' -> '.join(cycle)}")


# ===== Task Parsing =====


def parse_tasks_from_markdown(markdown: str) -> List[Task]:
    """
    Parse tasks from markdown format (as in tasks.md).

    Expected format:
    - [ ] **T001 Task description [P]**
      - Dependencies: T001, T002
      - Description: Detailed description

    Args:
        markdown: Markdown content containing task definitions

    Returns:
        List of parsed Task objects
    """
    tasks = []

    # Pattern to match task definitions
    # Matches: - [ ] **T001 description**
    task_pattern = re.compile(r"- \[ \] \*\*([A-Za-z0-9_-]+)\s+([^*]*(?:\*[^*]*)*)\*\*")

    # Pattern to extract dependencies
    # Matches: - Dependencies: T001, T002
    dep_pattern = re.compile(r"-[\s*]*Dependencies[:\s]+([^\n]+)", re.IGNORECASE)

    # Pattern to extract description
    # Matches: - Description: text
    desc_pattern = re.compile(r"-[\s*]*Description[:\s]+([^\n]+)", re.IGNORECASE)

    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line defines a task
        task_match = task_pattern.search(line)
        if task_match:
            task_id = task_match.group(1).strip()
            description = task_match.group(2).strip()

            # Check for [P] marker in description
            parallel = "[P]" in description

            # Clean up description
            description = description.replace("[P]", "").strip()

            # Look ahead for dependencies and description
            dependencies = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("-"):
                dep_match = dep_pattern.search(lines[j])
                if dep_match:
                    dep_str = dep_match.group(1).strip()
                    # Parse comma-separated dependencies
                    # Filter out "None" and empty strings
                    dependencies = [
                        d.strip()
                        for d in dep_str.split(",")
                        if d.strip() and d.strip().lower() != "none"
                    ]
                    break
                j += 1

            # Create task
            task = Task(
                id=task_id,
                description=description,
                dependencies=dependencies,
                parallel=parallel,
            )
            tasks.append(task)

        i += 1

    return tasks


# ===== Dependency Analysis =====


def analyze_dependencies(tasks: List[Task]) -> Dict[str, List[str]]:
    """
    Analyze task dependencies and build dependency graph.

    Args:
        tasks: List of tasks to analyze

    Returns:
        Dictionary mapping task_id to list of dependency IDs
    """
    graph = {}

    for task in tasks:
        graph[task.id] = task.dependencies.copy()

    return graph


def topological_sort(tasks: List[Task]) -> List[Task]:
    """
    Sort tasks topologically based on dependencies.

    Args:
        tasks: List of tasks to sort

    Returns:
        Tasks sorted in dependency order

    Raises:
        CircularDependencyError: If circular dependencies are detected
    """
    # Build dependency graph
    graph = analyze_dependencies(tasks)
    task_map = {task.id: task for task in tasks}

    # Kahn's algorithm for topological sort
    in_degree: Dict[str, int] = {task_id: 0 for task_id in graph}

    # Calculate in-degrees
    for task_id in graph:
        for dep in graph[task_id]:
            if dep in in_degree:
                in_degree[task_id] += 1

    # Queue of nodes with no dependencies
    queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
    sorted_tasks = []

    # Track visited for cycle detection
    visited: Set[str] = set()

    while queue:
        # Get a task with no dependencies
        task_id = queue.pop(0)

        if task_id in visited:
            continue
        visited.add(task_id)

        # Add to result
        if task_id in task_map:
            sorted_tasks.append(task_map[task_id])

        # Reduce in-degree for dependent tasks
        for dependent, deps in graph.items():
            if task_id in deps:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    # Check for cycles
    if len(sorted_tasks) != len(tasks):
        # Find cycle
        cycle = _find_cycle(graph)
        raise CircularDependencyError(cycle)

    return sorted_tasks


def _find_cycle(graph: Dict[str, List[str]]) -> List[str]:
    """
    Find a cycle in the dependency graph using DFS.

    Args:
        graph: Dependency graph

    Returns:
        List of task IDs forming a cycle
    """
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    path: List[str] = []

    def dfs(node: str) -> Optional[List[str]]:
        """DFS to find cycle."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                result = dfs(neighbor)
                if result:
                    return result
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]

        path.pop()
        rec_stack.remove(node)
        return None

    for node in graph:
        if node not in visited:
            result = dfs(node)
            if result:
                return result

    return []


# ===== Parallel Task Grouping =====


def group_parallel_tasks(tasks: List[Task]) -> List[List[Task]]:
    """
    Group tasks that can be executed in parallel.

    Tasks in the same group have no dependencies on each other
    and are marked as parallel=True.

    Args:
        tasks: Tasks sorted in dependency order

    Returns:
        List of task groups, where each group can be executed in parallel
    """
    if not tasks:
        return []

    groups: List[List[Task]] = []
    completed_ids: Set[str] = set()

    i = 0
    while i < len(tasks):
        task = tasks[i]

        # Check if all dependencies are satisfied
        deps_satisfied = all(dep in completed_ids for dep in task.dependencies)

        if not deps_satisfied:
            # Task can't be executed yet, add to completed and move on
            # (shouldn't happen if tasks are topologically sorted)
            groups.append([task])
            completed_ids.add(task.id)
            i += 1
            continue

        # Start a new group with this task
        current_group = [task]

        # Look for more tasks that can be executed in parallel
        j = i + 1
        while j < len(tasks):
            next_task = tasks[j]

            # Check if next task can be parallel
            # 1. All dependencies satisfied
            # 2. Marked as parallel
            # 3. Doesn't depend on tasks in current group
            next_deps_satisfied = all(
                dep in completed_ids or dep in {t.id for t in current_group}
                for dep in next_task.dependencies
            )

            can_be_parallel = (
                next_deps_satisfied
                and next_task.parallel
                and task.parallel
                and not any(
                    dep in {t.id for t in current_group}
                    for dep in next_task.dependencies
                )
            )

            if can_be_parallel:
                current_group.append(next_task)
                j += 1
            else:
                break

        # Add the group
        groups.append(current_group)
        for t in current_group:
            completed_ids.add(t.id)

        i = j

    return groups


# ===== Task Execution =====


def execute_task(task: Task, agent: Any) -> TaskResult:
    """
    Execute a single task using the Agent.

    Args:
        task: Task to execute
        agent: Agent instance for code generation

    Returns:
        TaskResult with execution outcome
    """
    start_time = time.time()

    try:
        # Update task status
        task.status = TaskStatus.IN_PROGRESS

        # Build prompt for agent
        prompt = _build_task_prompt(task)

        # Execute via agent
        turn = agent.process(prompt)

        # Update task status
        task.status = TaskStatus.COMPLETED

        end_time = time.time()

        return TaskResult(
            task_id=task.id,
            success=True,
            output=turn.content if hasattr(turn, "content") else str(turn),
            execution_time=end_time - start_time,
            start_time=start_time,
            end_time=end_time,
        )

    except Exception as e:
        # Task failed
        task.status = TaskStatus.FAILED
        end_time = time.time()

        return TaskResult(
            task_id=task.id,
            success=False,
            output="",
            error=str(e),
            execution_time=end_time - start_time,
            start_time=start_time,
            end_time=end_time,
        )


def _build_task_prompt(task: Task) -> str:
    """
    Build a prompt for the agent to execute the task.

    Args:
        task: Task to execute

    Returns:
        Prompt string for agent
    """
    parts = []

    # Add task description
    parts.append(f"Task: {task.id}")
    parts.append(f"Description: {task.description}")

    # Add TDD instruction
    if task.tdd:
        parts.append("\nIMPORTANT: Follow TDD principles - write tests first, then implement.")

    # Add file/function context
    if task.file:
        parts.append(f"\nTarget file: {task.file}")
    if task.function:
        parts.append(f"Target function: {task.function}")

    # Add dependencies context
    if task.dependencies:
        parts.append(f"\nDependencies: {', '.join(task.dependencies)}")

    parts.append("\nPlease implement this task according to the specification.")

    return "\n".join(parts)


# ===== Task Executor =====


@dataclass
class TaskExecutorConfig:
    """Configuration for TaskExecutor."""

    agent: Any
    max_parallel_tasks: int = 1
    continue_on_error: bool = True


@dataclass
class ExecutorStatus:
    """Status of task executor."""

    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    in_progress_tasks: int


class TaskExecutor:
    """
    Executes tasks in dependency order with parallel support.

    Features:
    - Topological sort for dependency ordering
    - Parallel execution for independent tasks marked [P]
    - Integration with Agent for code generation
    - Status tracking and error handling

    Usage:
        agent = Agent(config)
        executor = TaskExecutor(TaskExecutorConfig(agent=agent))
        results = executor.execute(tasks)
    """

    def __init__(self, config: TaskExecutorConfig) -> None:
        """
        Initialize TaskExecutor.

        Args:
            config: Executor configuration
        """
        self._config = config
        self._results: List[TaskResult] = []

    def execute(self, tasks: List[Task]) -> List[TaskResult]:
        """
        Execute tasks in dependency order.

        Args:
            tasks: List of tasks to execute

        Returns:
            List of task results
        """
        if not tasks:
            return []

        # Sort tasks topologically
        sorted_tasks = topological_sort(tasks)

        # Group tasks for parallel execution
        groups = group_parallel_tasks(sorted_tasks)

        # Execute each group
        all_results = []

        for group in groups:
            if len(group) == 1 or self._config.max_parallel_tasks <= 1:
                # Sequential execution
                for task in group:
                    result = execute_task(task, self._config.agent)
                    all_results.append(result)

                    # Stop if task failed and not continuing on error
                    if not result.success and not self._config.continue_on_error:
                        break
            else:
                # Parallel execution (simplified for MVP)
                # In MVP, we still execute sequentially but respect the grouping
                for task in group:
                    result = execute_task(task, self._config.agent)
                    all_results.append(result)

                    # Stop if task failed and not continuing on error
                    if not result.success and not self._config.continue_on_error:
                        break

        self._results = all_results
        return all_results

    def get_status(self) -> ExecutorStatus:
        """
        Get current execution status.

        Returns:
            ExecutorStatus with current state
        """
        total = len(self._results)
        completed = sum(1 for r in self._results if r.success)
        failed = sum(1 for r in self._results if not r.success)

        return ExecutorStatus(
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            in_progress_tasks=0,  # Tasks complete quickly, so this is 0
        )

    def get_results(self) -> List[TaskResult]:
        """
        Get execution results.

        Returns:
            List of task results
        """
        return list(self._results)

    def reset(self) -> None:
        """Reset executor state."""
        self._results = []
