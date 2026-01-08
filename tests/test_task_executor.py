"""
Tests for Task Executor (T114)

Tests cover:
- Task data model for execution
- Task parsing from tasks.md format
- Dependency analysis (topological sort)
- Sequential task execution
- Parallel task execution for [P] marked tasks
- Agent integration for code generation
- Task status and result tracking

Python 3.8.10 compatible
TDD: Red → Green → Refactor
"""

import pytest
from typing import Any, Dict, List
from dataclasses import dataclass
from enum import Enum
import time


# These will be imported from claude_code.core.sdd
# For now, we define them minimally for tests


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses: List[str] = None):
        """Initialize with predefined responses."""
        self.responses = responses or []
        self.call_count = 0

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """Return predefined response."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return self._create_response(response)
        return self._create_response("Default response")

    def _create_response(self, content: str) -> Any:
        """Create a mock response object."""

        @dataclass
        class MockResponse:
            content: str
            finish_reason: str = "stop"

        return MockResponse(content=content)


class MockAgent:
    """Mock Agent for testing."""

    def __init__(self, responses: List[str] = None):
        """Initialize with predefined responses."""
        self.llm = MockLLMClient(responses)
        self.process_count = 0
        self.last_input = None

    def process(self, user_input: str) -> Any:
        """Process user input and return mock response."""

        @dataclass
        class MockTurn:
            content: str
            finish_reason: str = "stop"
            tool_calls: Any = None
            has_tools: bool = False

        self.process_count += 1
        self.last_input = user_input
        return MockTurn(content=f"Response {self.process_count}: {user_input[:20]}")


# We'll import these after implementation
# from claude_code.core.sdd import (
#     Task,
#     TaskStatus,
#     TaskResult,
#     TaskExecutionError,
#     CircularDependencyError,
#     TaskExecutor,
#     TaskExecutorConfig,
#     parse_tasks_from_markdown,
#     analyze_dependencies,
#     topological_sort,
#     execute_task,
#     group_parallel_tasks,
# )


# ===== Task Data Model Tests =====


def test_task_creation_minimal():
    """Test creating a task with minimal fields."""
    from claude_code.core.sdd import Task, TaskStatus

    task = Task(
        id="T001",
        description="Implement feature X",
    )

    assert task.id == "T001"
    assert task.description == "Implement feature X"
    assert task.phase is None
    assert task.dependencies == []
    assert task.parallel is False
    assert task.tdd is True
    assert task.file is None
    assert task.function is None
    assert task.status == TaskStatus.PENDING


def test_task_creation_full():
    """Test creating a task with all fields."""
    from claude_code.core.sdd import Task, TaskStatus

    task = Task(
        id="T002",
        description="Implement feature Y",
        phase="Phase A",
        dependencies=["T001"],
        parallel=True,
        tdd=True,
        file="claude_code/core/sdd.py",
        function="execute_tasks",
    )

    assert task.id == "T002"
    assert task.description == "Implement feature Y"
    assert task.phase == "Phase A"
    assert task.dependencies == ["T001"]
    assert task.parallel is True
    assert task.tdd is True
    assert task.file == "claude_code/core/sdd.py"
    assert task.function == "execute_tasks"


def test_task_status_enum():
    """Test TaskStatus enum values."""
    from claude_code.core.sdd import TaskStatus

    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.IN_PROGRESS.value == "in_progress"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"


def test_task_status_transitions():
    """Test task status transitions."""
    from claude_code.core.sdd import Task, TaskStatus

    task = Task(id="T001", description="Test task")

    # Initial status
    assert task.status == TaskStatus.PENDING

    # Mark as in progress
    task.status = TaskStatus.IN_PROGRESS
    assert task.status == TaskStatus.IN_PROGRESS

    # Mark as completed
    task.status = TaskStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED

    # Mark as failed
    task.status = TaskStatus.FAILED
    assert task.status == TaskStatus.FAILED


def test_task_result_creation():
    """Test creating task results."""
    from claude_code.core.sdd import TaskResult

    result = TaskResult(
        task_id="T001",
        success=True,
        output="Task completed successfully",
        execution_time=1.5,
    )

    assert result.task_id == "T001"
    assert result.success is True
    assert result.output == "Task completed successfully"
    assert result.execution_time == 1.5
    assert result.error is None


def test_task_result_failure():
    """Test creating failed task results."""
    from claude_code.core.sdd import TaskResult

    result = TaskResult(
        task_id="T002",
        success=False,
        output="",
        error="Task failed: dependency not met",
        execution_time=0.5,
    )

    assert result.task_id == "T002"
    assert result.success is False
    assert result.output == ""
    assert result.error == "Task failed: dependency not met"
    assert result.execution_time == 0.5


# ===== Task Parsing Tests =====


def test_parse_single_task():
    """Test parsing a single task from markdown."""
    from claude_code.core.sdd import parse_tasks_from_markdown

    markdown = """
- [ ] **T001 Implement feature X**
  - Description: Basic feature implementation
  - Dependencies: None
    """

    tasks = parse_tasks_from_markdown(markdown)

    assert len(tasks) == 1
    assert tasks[0].id == "T001"
    assert "feature X" in tasks[0].description or "Implement" in tasks[0].description


def test_parse_multiple_tasks():
    """Test parsing multiple tasks from markdown."""
    from claude_code.core.sdd import parse_tasks_from_markdown

    markdown = """
- [ ] **T001 Task one**
  - Description: First task

- [ ] **T002 Task two**
  - Description: Second task

- [ ] **T003 Task three**
  - Description: Third task
    """

    tasks = parse_tasks_from_markdown(markdown)

    assert len(tasks) == 3
    assert tasks[0].id == "T001"
    assert tasks[1].id == "T002"
    assert tasks[2].id == "T003"


def test_parse_task_with_dependencies():
    """Test parsing tasks with dependencies."""
    from claude_code.core.sdd import parse_tasks_from_markdown

    markdown = """
- [ ] **T001 First task**
  - Dependencies: None

- [ ] **T002 Second task**
  - Dependencies: T001

- [ ] **T003 Third task**
  - Dependencies: T001, T002
    """

    tasks = parse_tasks_from_markdown(markdown)

    assert len(tasks) == 3
    assert tasks[0].dependencies == []
    assert tasks[1].dependencies == ["T001"]
    assert tasks[2].dependencies == ["T001", "T002"]


def test_parse_parallel_marked_tasks():
    """Test parsing tasks marked as parallel [P]."""
    from claude_code.core.sdd import parse_tasks_from_markdown

    markdown = """
- [ ] **T001 Sequential task**
  - Dependencies: None

- [ ] **T002 Parallel task [P]**
  - Dependencies: T001

- [ ] **T003 Another parallel task [P]**
  - Dependencies: T001
    """

    tasks = parse_tasks_from_markdown(markdown)

    assert len(tasks) == 3
    assert tasks[0].parallel is False
    assert tasks[1].parallel is True
    assert tasks[2].parallel is True


# ===== Dependency Analysis Tests =====


def test_analyze_dependencies_linear():
    """Test dependency analysis for linear chain."""
    from claude_code.core.sdd import Task, analyze_dependencies

    tasks = [
        Task(id="T001", description="First"),
        Task(id="T002", description="Second", dependencies=["T001"]),
        Task(id="T003", description="Third", dependencies=["T002"]),
    ]

    graph = analyze_dependencies(tasks)

    assert "T001" in graph
    assert "T002" in graph
    assert "T003" in graph
    assert graph["T001"] == []
    assert graph["T002"] == ["T001"]
    assert graph["T003"] == ["T002"]


def test_analyze_dependencies_diamond():
    """Test dependency analysis for diamond pattern."""
    from claude_code.core.sdd import Task, analyze_dependencies

    tasks = [
        Task(id="T001", description="Root"),
        Task(id="T002", description="Branch A", dependencies=["T001"]),
        Task(id="T003", description="Branch B", dependencies=["T001"]),
        Task(id="T004", description="Join", dependencies=["T002", "T003"]),
    ]

    graph = analyze_dependencies(tasks)

    assert set(graph["T004"]) == {"T002", "T003"}
    assert graph["T002"] == ["T001"]
    assert graph["T003"] == ["T001"]
    assert graph["T001"] == []


def test_topological_sort_linear():
    """Test topological sort for linear dependencies."""
    from claude_code.core.sdd import Task, topological_sort

    tasks = [
        Task(id="T001", description="First"),
        Task(id="T002", description="Second", dependencies=["T001"]),
        Task(id="T003", description="Third", dependencies=["T002"]),
    ]

    sorted_tasks = topological_sort(tasks)

    assert len(sorted_tasks) == 3
    assert sorted_tasks[0].id == "T001"
    assert sorted_tasks[1].id == "T002"
    assert sorted_tasks[2].id == "T003"


def test_topological_sort_complex():
    """Test topological sort for complex dependency graph."""
    from claude_code.core.sdd import Task, topological_sort

    tasks = [
        Task(id="T001", description="Root"),
        Task(id="T002", description="A", dependencies=["T001"]),
        Task(id="T003", description="B", dependencies=["T001"]),
        Task(id="T004", description="C", dependencies=["T002", "T003"]),
    ]

    sorted_tasks = topological_sort(tasks)

    assert len(sorted_tasks) == 4
    # T001 must be first
    assert sorted_tasks[0].id == "T001"
    # T004 must be last (depends on T002 and T003)
    assert sorted_tasks[3].id == "T004"
    # T002 and T003 must come before T004
    t002_idx = next(i for i, t in enumerate(sorted_tasks) if t.id == "T002")
    t003_idx = next(i for i, t in enumerate(sorted_tasks) if t.id == "T003")
    t004_idx = next(i for i, t in enumerate(sorted_tasks) if t.id == "T004")
    assert t002_idx < t004_idx
    assert t003_idx < t004_idx


def test_topological_sort_circular_dependency():
    """Test that circular dependencies are detected."""
    from claude_code.core.sdd import Task, topological_sort, CircularDependencyError

    tasks = [
        Task(id="T001", description="First", dependencies=["T002"]),
        Task(id="T002", description="Second", dependencies=["T001"]),
    ]

    with pytest.raises(CircularDependencyError) as exc_info:
        topological_sort(tasks)

    assert "circular" in str(exc_info.value).lower()


def test_topological_sort_self_dependency():
    """Test that self-dependencies are detected."""
    from claude_code.core.sdd import Task, topological_sort, CircularDependencyError

    tasks = [
        Task(id="T001", description="First", dependencies=["T001"]),
    ]

    with pytest.raises(CircularDependencyError) as exc_info:
        topological_sort(tasks)

    assert "circular" in str(exc_info.value).lower()


# ===== Parallel Task Grouping Tests =====


def test_group_parallel_tasks_none():
    """Test grouping when no tasks are parallel."""
    from claude_code.core.sdd import Task, group_parallel_tasks

    tasks = [
        Task(id="T001", description="First", parallel=False),
        Task(id="T002", description="Second", dependencies=["T001"], parallel=False),
    ]

    groups = group_parallel_tasks(tasks)

    assert len(groups) == 2
    assert all(len(g) == 1 for g in groups)


def test_group_parallel_tasks_simple():
    """Test grouping independent parallel tasks."""
    from claude_code.core.sdd import Task, group_parallel_tasks

    tasks = [
        Task(id="T001", description="Root"),
        Task(id="T002", description="Parallel A", dependencies=["T001"], parallel=True),
        Task(id="T003", description="Parallel B", dependencies=["T001"], parallel=True),
    ]

    groups = group_parallel_tasks(tasks)

    # T001 is sequential
    # T002 and T003 can be parallel
    assert len(groups) == 2
    assert len(groups[0]) == 1  # T001
    assert groups[0][0].id == "T001"
    assert len(groups[1]) == 2  # T002, T003
    assert {t.id for t in groups[1]} == {"T002", "T003"}


def test_group_parallel_tasks_mixed():
    """Test grouping mixed parallel and sequential tasks."""
    from claude_code.core.sdd import Task, group_parallel_tasks

    tasks = [
        Task(id="T001", description="Root"),
        Task(id="T002", description="Parallel A", dependencies=["T001"], parallel=True),
        Task(id="T003", description="Parallel B", dependencies=["T001"], parallel=True),
        Task(id="T004", description="Sequential", dependencies=["T002", "T003"], parallel=False),
    ]

    groups = group_parallel_tasks(tasks)

    assert len(groups) == 3
    assert len(groups[0]) == 1  # T001
    assert len(groups[1]) == 2  # T002, T003
    assert len(groups[2]) == 1  # T004
    assert groups[2][0].id == "T004"


# ===== Task Execution Tests =====


def test_execute_task_mock_agent():
    """Test executing a task with mock agent."""
    from claude_code.core.sdd import Task, execute_task

    agent = MockAgent(responses=["Implementation complete"])
    task = Task(
        id="T001",
        description="Implement feature X",
        file="test.py",
    )

    result = execute_task(task, agent)

    assert result.success is True
    assert result.task_id == "T001"
    assert agent.process_count == 1


def test_execute_task_with_tdd():
    """Test executing a task with TDD flag."""
    from claude_code.core.sdd import Task, execute_task

    agent = MockAgent(responses=["Test written", "Implementation complete"])
    task = Task(
        id="T001",
        description="Implement feature X with TDD",
        tdd=True,
        file="test.py",
    )

    result = execute_task(task, agent)

    assert result.success is True
    assert result.task_id == "T001"
    # Agent should be called once per task (TDD prompt includes test instruction)
    assert agent.process_count >= 1


def test_execute_task_multiple_calls():
    """Test that task execution prompts agent appropriately."""
    from claude_code.core.sdd import Task, execute_task

    agent = MockAgent(responses=["Step 1", "Step 2", "Step 3"])
    task = Task(
        id="T001",
        description="Implement feature X with tests",
        tdd=True,
    )

    result = execute_task(task, agent)

    assert result.success is True
    # Agent should be called once per task
    assert agent.process_count >= 1


# ===== TaskExecutor Tests =====


def test_executor_initialization():
    """Test TaskExecutor initialization."""
    from claude_code.core.sdd import TaskExecutor, TaskExecutorConfig

    agent = MockAgent()
    config = TaskExecutorConfig(agent=agent, max_parallel_tasks=2)

    executor = TaskExecutor(config)

    assert executor._config.agent == agent
    assert executor._config.max_parallel_tasks == 2
    status = executor.get_status()
    assert status.total_tasks == 0
    assert status.completed_tasks == 0
    assert status.failed_tasks == 0


def test_executor_sequential_execution():
    """Test sequential execution of tasks."""
    from claude_code.core.sdd import Task, TaskExecutor, TaskExecutorConfig

    agent = MockAgent(responses=["Done 1", "Done 2", "Done 3"])
    config = TaskExecutorConfig(agent=agent)

    tasks = [
        Task(id="T001", description="Task 1"),
        Task(id="T002", description="Task 2", dependencies=["T001"]),
        Task(id="T003", description="Task 3", dependencies=["T002"]),
    ]

    executor = TaskExecutor(config)
    results = executor.execute(tasks)

    assert len(results) == 3
    assert all(r.success for r in results)
    assert results[0].task_id == "T001"
    assert results[1].task_id == "T002"
    assert results[2].task_id == "T003"

    # Verify execution order
    assert agent.process_count == 3


def test_executor_with_independent_tasks():
    """Test executor with independent tasks (no dependencies)."""
    from claude_code.core.sdd import Task, TaskExecutor, TaskExecutorConfig

    agent = MockAgent(responses=["A", "B", "C"])
    config = TaskExecutorConfig(agent=agent)

    tasks = [
        Task(id="T001", description="Task A"),
        Task(id="T002", description="Task B"),
        Task(id="T003", description="Task C"),
    ]

    executor = TaskExecutor(config)
    results = executor.execute(tasks)

    assert len(results) == 3
    assert all(r.success for r in results)


def test_executor_parallel_marked_tasks():
    """Test executor respects [P] marking for parallel tasks."""
    from claude_code.core.sdd import Task, TaskExecutor, TaskExecutorConfig

    agent = MockAgent(responses=["A", "B", "C"])
    config = TaskExecutorConfig(agent=agent, max_parallel_tasks=2)

    tasks = [
        Task(id="T001", description="Root"),
        Task(id="T002", description="Parallel A", dependencies=["T001"], parallel=True),
        Task(id="T003", description="Parallel B", dependencies=["T001"], parallel=True),
    ]

    executor = TaskExecutor(config)
    results = executor.execute(tasks)

    assert len(results) == 3
    assert all(r.success for r in results)


def test_executor_status_tracking():
    """Test that executor tracks task status correctly."""
    from claude_code.core.sdd import Task, TaskExecutor, TaskExecutorConfig

    agent = MockAgent(responses=["Done"])
    config = TaskExecutorConfig(agent=agent)

    tasks = [
        Task(id="T001", description="Task 1"),
        Task(id="T002", description="Task 2", dependencies=["T001"]),
    ]

    executor = TaskExecutor(config)

    # Initial status
    status = executor.get_status()
    assert status.total_tasks == 0
    assert status.completed_tasks == 0
    assert status.failed_tasks == 0

    # Execute tasks
    results = executor.execute(tasks)

    # Final status
    status = executor.get_status()
    assert status.total_tasks == 2
    assert status.completed_tasks == 2
    assert status.failed_tasks == 0


def test_executor_empty_task_list():
    """Test executor with empty task list."""
    from claude_code.core.sdd import TaskExecutor, TaskExecutorConfig

    agent = MockAgent()
    config = TaskExecutorConfig(agent=agent)

    executor = TaskExecutor(config)
    results = executor.execute([])

    assert len(results) == 0


def test_executor_task_failure():
    """Test executor handles task failures gracefully."""
    from claude_code.core.sdd import Task, TaskExecutor, TaskExecutorConfig

    class FailingAgent(MockAgent):
        def process(self, user_input: str) -> Any:
            raise Exception("Task execution failed")

    agent = FailingAgent()
    config = TaskExecutorConfig(agent=agent)

    tasks = [
        Task(id="T001", description="Failing task"),
    ]

    executor = TaskExecutor(config)
    results = executor.execute(tasks)

    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error is not None


def test_executor_diamond_dependencies():
    """Test executor with diamond dependency pattern."""
    from claude_code.core.sdd import Task, TaskExecutor, TaskExecutorConfig

    agent = MockAgent(responses=["A", "B", "C", "D"])
    config = TaskExecutorConfig(agent=agent)

    tasks = [
        Task(id="T001", description="Root"),
        Task(id="T002", description="Branch A", dependencies=["T001"]),
        Task(id="T003", description="Branch B", dependencies=["T001"]),
        Task(id="T004", description="Join", dependencies=["T002", "T003"]),
    ]

    executor = TaskExecutor(config)
    results = executor.execute(tasks)

    assert len(results) == 4
    assert all(r.success for r in results)


# ===== Integration Tests =====


def test_full_workflow_sequential():
    """Test full workflow: parse → analyze → execute sequential."""
    from claude_code.core.sdd import (
        parse_tasks_from_markdown,
        topological_sort,
        TaskExecutor,
        TaskExecutorConfig,
    )

    markdown = """
- [ ] **T001 Create base model**
  - Description: Create the base data model
  - Dependencies: None

- [ ] **T002 Implement parser**
  - Description: Parse tasks from markdown
  - Dependencies: T001

- [ ] **T003 Implement executor**
  - Description: Execute tasks in order
  - Dependencies: T002
    """

    # Parse
    tasks = parse_tasks_from_markdown(markdown)
    assert len(tasks) == 3

    # Analyze
    sorted_tasks = topological_sort(tasks)
    assert sorted_tasks[0].id == "T001"

    # Execute
    agent = MockAgent(responses=["Model done", "Parser done", "Executor done"])
    config = TaskExecutorConfig(agent=agent)
    executor = TaskExecutor(config)

    results = executor.execute(sorted_tasks)

    assert len(results) == 3
    assert all(r.success for r in results)


def test_full_workflow_with_parallel():
    """Test full workflow with parallel tasks."""
    from claude_code.core.sdd import (
        parse_tasks_from_markdown,
        TaskExecutor,
        TaskExecutorConfig,
    )

    markdown = """
- [ ] **T001 Setup project**
  - Dependencies: None

- [ ] **T002 Implement feature A [P]**
  - Dependencies: T001

- [ ] **T003 Implement feature B [P]**
  - Dependencies: T001

- [ ] **T004 Integration tests**
  - Dependencies: T002, T003
    """

    # Parse
    tasks = parse_tasks_from_markdown(markdown)
    assert len(tasks) == 4

    # Verify parallel marking
    assert tasks[1].parallel is True
    assert tasks[2].parallel is True

    # Execute
    agent = MockAgent(responses=["Setup", "Feature A", "Feature B", "Tests"])
    config = TaskExecutorConfig(agent=agent)
    executor = TaskExecutor(config)

    results = executor.execute(tasks)

    assert len(results) == 4
    assert all(r.success for r in results)


# ===== Error Handling Tests =====


def test_missing_dependency():
    """Test executor with missing dependency."""
    from claude_code.core.sdd import Task, TaskExecutor, TaskExecutorConfig

    agent = MockAgent(responses=["Done"])
    config = TaskExecutorConfig(agent=agent)

    tasks = [
        Task(id="T001", description="Task with missing dep", dependencies=["T999"]),
    ]

    executor = TaskExecutor(config)
    # Should handle gracefully - missing deps are just not found
    results = executor.execute(tasks)

    assert len(results) == 1


def test_executor_invalid_task_id():
    """Test executor handles various task ID formats."""
    from claude_code.core.sdd import Task, TaskExecutor, TaskExecutorConfig

    agent = MockAgent(responses=["Done"])
    config = TaskExecutorConfig(agent=agent)

    tasks = [
        Task(id="T-001", description="Task with dash"),
        Task(id="TASK-100", description="Task with prefix"),
        Task(id="123", description="Numeric ID"),
    ]

    executor = TaskExecutor(config)
    results = executor.execute(tasks)

    assert len(results) == 3
    assert all(r.success for r in results)


# ===== Performance Tests =====


def test_executor_many_tasks():
    """Test executor handles many tasks efficiently."""
    from claude_code.core.sdd import Task, TaskExecutor, TaskExecutorConfig

    responses = [f"Task {i} done" for i in range(20)]
    agent = MockAgent(responses=responses)
    config = TaskExecutorConfig(agent=agent)

    # Create chain of dependent tasks
    tasks = []
    for i in range(20):
        deps = [f"T{i:03d}"] if i > 0 else []
        tasks.append(
            Task(id=f"T{i+1:03d}", description=f"Task {i}", dependencies=deps)
        )

    executor = TaskExecutor(config)
    results = executor.execute(tasks)

    assert len(results) == 20
    assert all(r.success for r in results)
    assert agent.process_count == 20
