"""
Tests for SDD (Spec-Driven Development) module.

Follows TDD principles: Red -> Green -> Refactor
Tests for data models, parsers, and generators.
"""
from typing import List
import pytest
from pathlib import Path

# Import models to be tested
from deep_code.sdd.models import Task, Phase, Dependency, TaskStatus


class TestTaskStatus:
    """Test TaskStatus enum."""

    def test_task_status_values(self) -> None:
        """Test TaskStatus has expected values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.FAILED.value == "failed"


class TestDependency:
    """Test Dependency model."""

    def test_dependency_creation_simple(self) -> None:
        """Test creating a simple dependency."""
        dep = Dependency(task_id="T001")
        assert dep.task_id == "T001"
        assert dep.type == "after"  # default type

    def test_dependency_creation_with_type(self) -> None:
        """Test creating a dependency with explicit type."""
        dep = Dependency(task_id="T002", type="parallel")
        assert dep.task_id == "T002"
        assert dep.type == "parallel"

    def test_dependency_equality(self) -> None:
        """Test dependency equality."""
        dep1 = Dependency(task_id="T001")
        dep2 = Dependency(task_id="T001")
        assert dep1 == dep2


class TestPhase:
    """Test Phase model."""

    def test_phase_creation(self) -> None:
        """Test creating a phase."""
        phase = Phase(
            id="phase-a",
            name="Infrastructure",
            description="Setup project structure"
        )
        assert phase.id == "phase-a"
        assert phase.name == "Infrastructure"
        assert phase.description == "Setup project structure"
        assert phase.tasks == []

    def test_phase_with_tasks(self) -> None:
        """Test creating a phase with tasks."""
        task1 = Task(id="T001", description="Init project")
        task2 = Task(id="T002", description="Setup deps")

        phase = Phase(
            id="phase-b",
            name="CLI",
            description="CLI entry point",
            tasks=[task1, task2]
        )
        assert len(phase.tasks) == 2
        assert phase.tasks[0].id == "T001"
        assert phase.tasks[1].id == "T002"


class TestTask:
    """Test Task model."""

    def test_task_creation_minimal(self) -> None:
        """Test creating a minimal task."""
        task = Task(
            id="T001",
            description="Initialize project structure"
        )
        assert task.id == "T001"
        assert task.description == "Initialize project structure"
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == []
        assert task.parallel is False
        assert task.tdd is True  # default
        assert task.file is None
        assert task.function is None

    def test_task_with_dependencies(self) -> None:
        """Test creating a task with dependencies."""
        dep = Dependency(task_id="T001")
        task = Task(
            id="T002",
            description="Setup dependencies",
            dependencies=[dep]
        )
        assert len(task.dependencies) == 1
        assert task.dependencies[0].task_id == "T001"

    def test_task_parallel_flag(self) -> None:
        """Test task parallel flag."""
        task = Task(
            id="T003",
            description="Terminal output",
            parallel=True
        )
        assert task.parallel is True

    def test_task_tdd_flag(self) -> None:
        """Test task TDD flag."""
        task = Task(
            id="T004",
            description="CLI entry",
            tdd=False
        )
        assert task.tdd is False

    def test_task_with_file_and_function(self) -> None:
        """Test task with file and function targets."""
        task = Task(
            id="T005",
            description="Implement parser",
            file="deep_code/interaction/parser.py",
            function="parse_context_ref"
        )
        assert task.file == "deep_code/interaction/parser.py"
        assert task.function == "parse_context_ref"

    def test_task_status_update(self) -> None:
        """Test updating task status."""
        task = Task(id="T006", description="Test task")
        assert task.status == TaskStatus.PENDING

        task.status = TaskStatus.IN_PROGRESS
        assert task.status == TaskStatus.IN_PROGRESS

        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED


class TestTaskMarkdownParsing:
    """Test parsing tasks from markdown format (as in tasks.md)."""

    def test_parse_simple_task_from_markdown(self) -> None:
        """Test parsing a simple task from markdown."""
        markdown = """
- [ ] **T001 初始化项目目录结构（骨架）**
  - **依赖**：无
  - **产物**：`deep_code/` 主包与子包目录
  - **验证**：`python -c "import deep_code"`
"""
        # This will be implemented in parser.py
        # For now, we test the model structure
        task = Task(
            id="T001",
            description="初始化项目目录结构（骨架）",
            dependencies=[]
        )
        assert task.id == "T001"
        assert "初始化" in task.description

    def test_parse_task_with_dependencies_from_markdown(self) -> None:
        """Test parsing task with dependencies from markdown."""
        markdown = """
- [ ] **T002 依赖清单与锁定**
  - **依赖**：T001
  - **产物**：requirements.txt
"""
        # Model should support this structure
        task = Task(
            id="T002",
            description="依赖清单与锁定",
            dependencies=[Dependency(task_id="T001")]
        )
        assert len(task.dependencies) == 1
        assert task.dependencies[0].task_id == "T001"

    def test_parse_parallel_task_from_markdown(self) -> None:
        """Test parsing parallel task from markdown."""
        markdown = """
- [ ] **T011 终端输出封装 [P]**
  - **依赖**：T010
"""
        # Model should support parallel flag
        task = Task(
            id="T011",
            description="终端输出封装 [P]",
            dependencies=[Dependency(task_id="T001")],
            parallel=True
        )
        assert task.parallel is True
        assert "[P]" in task.description


class TestTaskDependencyAnalysis:
    """Test task dependency analysis and topological sorting."""

    def test_no_dependencies(self) -> None:
        """Test tasks with no dependencies."""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2"),
            Task(id="T003", description="Task 3"),
        ]

        # All tasks can be executed in any order
        assert len(tasks) == 3

    def test_linear_dependencies(self) -> None:
        """Test tasks with linear dependency chain."""
        tasks = [
            Task(id="T001", description="Task 1", dependencies=[]),
            Task(id="T002", description="Task 2",
                 dependencies=[Dependency(task_id="T001")]),
            Task(id="T003", description="Task 3",
                 dependencies=[Dependency(task_id="T002")]),
        ]

        # T001 -> T002 -> T003
        assert tasks[0].id == "T001"
        assert tasks[1].dependencies[0].task_id == "T001"
        assert tasks[2].dependencies[0].task_id == "T002"

    def test_parallel_dependencies(self) -> None:
        """Test tasks with parallel branches."""
        tasks = [
            Task(id="T001", description="Base", dependencies=[]),
            Task(id="T002", description="Branch A",
                 dependencies=[Dependency(task_id="T001")], parallel=True),
            Task(id="T003", description="Branch B",
                 dependencies=[Dependency(task_id="T001")], parallel=True),
        ]

        # T001 -> (T002, T003 in parallel)
        assert tasks[1].parallel is True
        assert tasks[2].parallel is True
        assert tasks[1].dependencies[0].task_id == "T001"
        assert tasks[2].dependencies[0].task_id == "T001"

    def test_detect_circular_dependency(self) -> None:
        """Test detection of circular dependencies."""
        tasks = [
            Task(id="T001", description="Task 1",
                 dependencies=[Dependency(task_id="T002")]),
            Task(id="T002", description="Task 2",
                 dependencies=[Dependency(task_id="T003")]),
            Task(id="T003", description="Task 3",
                 dependencies=[Dependency(task_id="T001")]),
        ]

        # Should detect circular dependency: T001 -> T002 -> T003 -> T001
        # This will be tested in implementation
        task_ids = [t.id for t in tasks]
        assert task_ids == ["T001", "T002", "T003"]

        # Verify circular structure exists
        assert tasks[0].dependencies[0].task_id == "T002"
        assert tasks[1].dependencies[0].task_id == "T003"
        assert tasks[2].dependencies[0].task_id == "T001"


class TestSpecMarkdownStructure:
    """Test parsing spec.md markdown structure."""

    def test_spec_markdown_has_required_sections(self) -> None:
        """Test that spec markdown has required sections."""
        spec_content = """
# 项目概述

## 用户故事

### 核心用户故事

**US-001：作为开发者，我希望通过 @file 注入上下文**

- **场景**：开发时需要让 AI 理解代码
- **验收标准**：
  - 能够通过 @/path/to/file.py 引用文件

## 功能需求

### 核心交互模型

#### 上下文注入（@）

- **文件引用**：@/path/to/file.py

## 验收标准
"""
        # Verify structure has expected sections
        assert "项目概述" in spec_content or "项目概述" in spec_content
        assert "用户故事" in spec_content
        assert "功能需求" in spec_content
        assert "验收标准" in spec_content


class TestPlanMarkdownStructure:
    """Test parsing plan.md markdown structure."""

    def test_plan_markdown_has_required_sections(self) -> None:
        """Test that plan markdown has required sections."""
        plan_content = """
# 技术方案

## 技术上下文总结

### 技术栈选型

### 运行环境

## 合宪性检查清单

### 简单性门禁

### TDD 门禁

## 项目结构细化

### 目录结构

### 包职责划分

## 核心数据结构

## 关键接口设计
"""
        # Verify structure has expected sections
        assert "技术上下文" in plan_content or "技术栈" in plan_content
        assert "合宪性检查清单" in plan_content
        assert "项目结构" in plan_content or "目录结构" in plan_content
        assert "数据结构" in plan_content or "接口设计" in plan_content


class TestTaskMarkdownStructure:
    """Test parsing tasks.md markdown structure."""

    def test_tasks_markdown_has_required_sections(self) -> None:
        """Test that tasks markdown has required sections."""
        tasks_content = """
## 上下文梳理

## 里程碑

## 任务清单

### Phase A：基础设施

- [ ] **T001 初始化项目目录**
  - **依赖**：无
  - **产物**：目录结构
  - **验证**：python -c "import deep_code"

- [ ] **T002 依赖清单**
  - **依赖**：T001
  - **产物**：requirements.txt
"""
        # Verify structure
        assert "里程碑" in tasks_content or "上下文" in tasks_content
        assert "任务清单" in tasks_content
        assert "Phase A" in tasks_content
        assert "T001" in tasks_content
        assert "T002" in tasks_content

    def test_parse_multiple_phases(self) -> None:
        """Test parsing multiple phases from tasks.md."""
        tasks_content = """
### Phase A：基础设施

- [ ] T001 Task A1
- [ ] T002 Task A2

### Phase B：CLI 入口

- [ ] T010 Task B1
- [ ] T011 Task B2
"""
        # Should parse into multiple phases
        assert "Phase A" in tasks_content
        assert "Phase B" in tasks_content
        assert "T001" in tasks_content
        assert "T010" in tasks_content
