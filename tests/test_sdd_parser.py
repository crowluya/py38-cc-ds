"""
SDD Parser Tests - Test tasks.md parsing functionality

TDD: Tests for T110 (Task model and parser)
Python 3.8.10 compatible
"""

from typing import List

import pytest

from claude_code.sdd.models import Dependency, Task
from claude_code.sdd.parser import TaskParseError, parse_tasks_markdown


class TestTaskParserMinimal:
    """Test basic task parsing functionality."""

    def test_parse_single_task_minimal(self) -> None:
        """验证解析单个最小任务"""
        markdown = "- [ ] **T001 Test task**\n"

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        assert tasks[0].id == "T001"
        assert tasks[0].description == "Test task"

    def test_parse_empty_markdown(self) -> None:
        """验证解析空文档"""
        tasks = parse_tasks_markdown("")

        assert len(tasks) == 0

    def test_parse_markdown_with_no_tasks(self) -> None:
        """验证解析无任务的markdown"""
        markdown = "# Some Header\n\nSome text\n\nNo tasks here\n"

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 0


class TestTaskParserWithFields:
    """Test parsing tasks with various fields."""

    def test_parse_task_with_dependencies(self) -> None:
        """验证解析带依赖的任务"""
        markdown = (
            "- [ ] **T001 Test task**\n"
            "  - **依赖**: T000\n"
            "  - **产物**: test.py\n"
        )

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        assert tasks[0].dependencies[0].task_id == "T000"
        assert tasks[0].file == "test.py"

    def test_parse_task_with_multiple_dependencies(self) -> None:
        """验证解析多个依赖"""
        markdown = "- [ ] **T002 Task**\n" "  - **依赖**: T001, T003, T005\n"

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        dep_ids = [d.task_id for d in tasks[0].dependencies]
        assert dep_ids == ["T001", "T003", "T005"]

    def test_parse_task_with_parallel_marker(self) -> None:
        """验证解析并行标记"""
        markdown = "- [ ] **T001 Test task [P]**\n"

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        assert tasks[0].parallel is True

    def test_parse_task_without_parallel_marker(self) -> None:
        """验证无并行标记时默认为False"""
        markdown = "- [ ] **T001 Test task**\n"

        tasks = parse_tasks_markdown(markdown)

        assert tasks[0].parallel is False

    def test_parse_completed_task(self) -> None:
        """验证解析已完成的任务"""
        markdown = "- [x] **T001 Done task**\n"

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        assert tasks[0].id == "T001"


class TestTaskParserMultipleTasks:
    """Test parsing multiple tasks."""

    def test_parse_multiple_tasks(self) -> None:
        """验证解析多个任务"""
        markdown = (
            "- [ ] **T001 First task**\n"
            "- [ ] **T002 Second task**\n"
            "  - **依赖**: T001\n"
        )

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 2
        assert tasks[0].id == "T001"
        assert tasks[1].id == "T002"
        assert tasks[1].dependencies[0].task_id == "T001"

    def test_parse_tasks_with_phase_headers(self) -> None:
        """验证解析带阶段头的任务"""
        markdown = (
            "### Phase A\n"
            "- [ ] **T001 Task A**\n"
            "\n"
            "### Phase B\n"
            "- [ ] **T002 Task B**\n"
            "  - **依赖**: T001\n"
        )

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 2
        assert tasks[0].id == "T001"
        assert tasks[1].id == "T002"
        assert tasks[1].dependencies[0].task_id == "T001"

    def test_parse_three_dependent_tasks(self) -> None:
        """验证解析三个依赖任务"""
        markdown = (
            "- [ ] **T001 First**\n"
            "- [ ] **T002 Second**\n"
            "  - **依赖**: T001\n"
            "- [ ] **T003 Third**\n"
            "  - **依赖**: T002\n"
        )

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 3
        assert tasks[0].id == "T001"
        assert tasks[1].dependencies[0].task_id == "T001"
        assert tasks[2].dependencies[0].task_id == "T002"


class TestTaskParserAllFields:
    """Test parsing tasks with all possible fields."""

    def test_parse_task_with_all_fields(self) -> None:
        """验证解析所有字段"""
        markdown = (
            "- [ ] **T001 Full task**\n"
            "  - **依赖**: T000\n"
            "  - **产物**: test.py\n"
            "  - **改动点**: test.py, tests/test.py\n"
            "  - **验证**: pytest\n"
            "  - **DoD**: Definition of Done\n"
        )

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        task = tasks[0]
        assert task.dependencies[0].task_id == "T000"
        assert task.file == "test.py"

    def test_parse_task_with_backticks(self) -> None:
        """验证解析带反引号的字段值"""
        markdown = (
            "- [ ] **T001 Task**\n" "  - **验证**: `python -c \"import test\"`\n"
        )

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        # Field value should have backticks removed
        assert tasks[0] is not None


class TestTaskParserEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_task_with_none_dependency(self) -> None:
        """验证解析'无'依赖"""
        markdown = "- [ ] **T001 Task**\n" "  - **依赖**: 无\n"

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        assert len(tasks[0].dependencies) == 0

    def test_parse_task_with_none_english_dependency(self) -> None:
        """验证解析'none'依赖"""
        markdown = "- [ ] **T001 Task**\n" "  - **Dependencies**: none\n"

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        assert len(tasks[0].dependencies) == 0

    def test_parse_task_with_empty_dependencies(self) -> None:
        """验证解析空依赖"""
        markdown = "- [ ] **T001 Task**\n" "  - **依赖**:\n"

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        # Empty dependencies should result in empty list
        assert len(tasks[0].dependencies) == 0


class TestTaskParserRealWorldExamples:
    """Test with real-world task examples from tasks.md."""

    def test_parse_real_task_t001(self) -> None:
        """验证解析真实任务T001"""
        markdown = (
            "- [ ] **T001 初始化项目目录结构（骨架）**\n"
            "  - **依赖**：无\n"
            "  - **产物**：`claude_code/` 主包与子包目录、`tests/` 目录、必要的 `__init__.py`\n"
            "  - **验证**：`python -c \"import claude_code\"`\n"
        )

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        task = tasks[0]
        assert task.id == "T001"
        assert "初始化" in task.description
        assert len(task.dependencies) == 0

    def test_parse_real_task_t011(self) -> None:
        """验证解析真实并行任务T011"""
        markdown = (
            "- [ ] **T011 终端输出封装（rich）[P]（TDD）**\n"
            "  - **依赖**：T010\n"
            "  - **产物**：输出工具层（如 `Console` 单例/工厂，但避免全局不可测状态）\n"
            "  - **验证**：单测覆盖 Markdown/代码块展示的基本路径\n"
        )

        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        task = tasks[0]
        assert task.id == "T011"
        assert task.parallel is True
        assert task.dependencies[0].task_id == "T010"


class TestTaskParserTableDriven:
    """Table-driven tests for parser (TDD requirement)."""

    @pytest.mark.parametrize(
        "markdown,expected_id,expected_description,expected_parallel",
        [
            # Basic task
            ("- [ ] **T001 Simple**", "T001", "Simple", False),
            # Task with [P]
            ("- [ ] **T002 Parallel [P]**", "T002", "Parallel", True),
            # Task with [P] and extra text (marker removed from description)
            ("- [ ] **T003 Task [P] (TDD)**", "T003", "Task  (TDD)", True),
            # Task with Chinese description
            ("- [ ] **T004 测试任务**", "T004", "测试任务", False),
            # Completed task
            ("- [x] **T005 Done**", "T005", "Done", False),
        ],
    )
    def test_parse_task_variations(
        self, markdown: str, expected_id: str, expected_description: str, expected_parallel: bool
    ) -> None:
        """表格驱动测试：各种任务格式"""
        tasks = parse_tasks_markdown(markdown)

        assert len(tasks) == 1
        assert tasks[0].id == expected_id
        assert tasks[0].description == expected_description
        assert tasks[0].parallel == expected_parallel
