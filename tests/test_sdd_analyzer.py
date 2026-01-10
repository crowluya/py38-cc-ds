"""
SDD Analyzer Tests - Test dependency analysis functionality

TDD: Tests for T113 (Dependency analysis with topological sort and cycle detection)
Python 3.8.10 compatible
"""

from typing import Any, Dict, List

import pytest

from deep_code.sdd.analyzer import CircularDependencyError, DependencyAnalyzer
from deep_code.sdd.models import Dependency, Task


class TestTopologicalSort:
    """Test topological sorting of tasks."""

    def test_topological_sort_no_dependencies(self) -> None:
        """验证无依赖任务的排序"""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2"),
            Task(id="T003", description="Task 3"),
        ]

        analyzer = DependencyAnalyzer(tasks)
        sorted_tasks = analyzer.topological_sort()

        assert len(sorted_tasks) == 3
        # All tasks should be present
        assert {t.id for t in sorted_tasks} == {"T001", "T002", "T003"}

    def test_topological_sort_linear_chain(self) -> None:
        """验证线性依赖链排序"""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T001")]),
            Task(id="T003", description="Task 3", dependencies=[Dependency(task_id="T002")]),
        ]

        analyzer = DependencyAnalyzer(tasks)
        sorted_tasks = analyzer.topological_sort()

        assert [t.id for t in sorted_tasks] == ["T001", "T002", "T003"]

    def test_topological_sort_diamond(self) -> None:
        """验证菱形依赖排序"""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T001")]),
            Task(id="T003", description="Task 3", dependencies=[Dependency(task_id="T001")]),
            Task(
                id="T004",
                description="Task 4",
                dependencies=[Dependency(task_id="T002"), Dependency(task_id="T003")],
            ),
        ]

        analyzer = DependencyAnalyzer(tasks)
        sorted_tasks = analyzer.topological_sort()

        # T001 must be first
        assert sorted_tasks[0].id == "T001"
        # T004 must be last (depends on both T002 and T003)
        assert sorted_tasks[-1].id == "T004"

        # Verify dependencies are satisfied
        task_ids = [t.id for t in sorted_tasks]
        t002_idx = task_ids.index("T002")
        t003_idx = task_ids.index("T003")
        t004_idx = task_ids.index("T004")

        assert t002_idx > task_ids.index("T001")
        assert t003_idx > task_ids.index("T001")
        assert t004_idx > t002_idx
        assert t004_idx > t003_idx

    def test_topological_sort_complex_dag(self) -> None:
        """验证复杂DAG排序"""
        tasks = [
            Task(id="T001", description="Base"),
            Task(id="T002", description="Branch A", dependencies=[Dependency(task_id="T001")]),
            Task(id="T003", description="Branch B", dependencies=[Dependency(task_id="T001")]),
            Task(id="T004", description="Merge", dependencies=[Dependency(task_id="T002")]),
            Task(id="T005", description="Final", dependencies=[Dependency(task_id="T003"), Dependency(task_id="T004")]),
        ]

        analyzer = DependencyAnalyzer(tasks)
        sorted_tasks = analyzer.topological_sort()

        task_ids = [t.id for t in sorted_tasks]

        # Verify ordering
        assert task_ids.index("T001") < task_ids.index("T002")
        assert task_ids.index("T001") < task_ids.index("T003")
        assert task_ids.index("T002") < task_ids.index("T004")
        assert task_ids.index("T003") < task_ids.index("T005")
        assert task_ids.index("T004") < task_ids.index("T005")


class TestCircularDependencyDetection:
    """Test circular dependency detection."""

    def test_detect_simple_cycle(self) -> None:
        """验证检测简单循环依赖"""
        tasks = [
            Task(id="T001", description="Task 1", dependencies=[Dependency(task_id="T002")]),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T001")]),
        ]

        analyzer = DependencyAnalyzer(tasks)

        with pytest.raises(CircularDependencyError) as exc_info:
            analyzer.topological_sort()

        # Verify error contains cycle information
        error_str = str(exc_info.value)
        assert "T001" in error_str
        assert "T002" in error_str
        assert "circular" in error_str.lower()

    def test_detect_complex_cycle(self) -> None:
        """验证检测复杂循环依赖"""
        tasks = [
            Task(id="T001", description="Task 1", dependencies=[Dependency(task_id="T002")]),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T003")]),
            Task(id="T003", description="Task 3", dependencies=[Dependency(task_id="T001")]),
        ]

        analyzer = DependencyAnalyzer(tasks)

        with pytest.raises(CircularDependencyError) as exc_info:
            analyzer.topological_sort()

        # Check error mentions the cycle
        error_str = str(exc_info.value)
        assert any(tid in error_str for tid in ["T001", "T002", "T003"])

    def test_detect_self_reference(self) -> None:
        """验证检测自引用循环"""
        tasks = [Task(id="T001", description="Task 1", dependencies=[Dependency(task_id="T001")])]

        analyzer = DependencyAnalyzer(tasks)

        with pytest.raises(CircularDependencyError):
            analyzer.topological_sort()

    def test_detect_multiple_cycles(self) -> None:
        """验证检测多个循环"""
        tasks = [
            Task(id="T001", description="Task 1", dependencies=[Dependency(task_id="T002")]),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T001")]),
            Task(id="T003", description="Task 3", dependencies=[Dependency(task_id="T004")]),
            Task(id="T004", description="Task 4", dependencies=[Dependency(task_id="T003")]),
        ]

        analyzer = DependencyAnalyzer(tasks)
        cycles = analyzer.detect_cycles()

        # Should detect at least one cycle
        assert len(cycles) >= 1

    def test_no_cycles_in_valid_dag(self) -> None:
        """验证有效DAG无循环"""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T001")]),
            Task(id="T003", description="Task 3", dependencies=[Dependency(task_id="T002")]),
        ]

        analyzer = DependencyAnalyzer(tasks)
        cycles = analyzer.detect_cycles()

        assert len(cycles) == 0


class TestParallelGroupAnalysis:
    """Test parallel execution group identification."""

    def test_get_parallel_groups_all_independent(self) -> None:
        """验证所有独立任务的并行分组"""
        tasks = [
            Task(id="T001", description="Task 1", parallel=True),
            Task(id="T002", description="Task 2", parallel=True),
            Task(id="T003", description="Task 3", parallel=True),
        ]

        analyzer = DependencyAnalyzer(tasks)
        groups = analyzer.get_parallel_groups()

        # All parallel-capable tasks at level 0
        assert len(groups) >= 1

    def test_get_parallel_groups_with_dependencies(self) -> None:
        """验证带依赖任务的并行分组"""
        tasks = [
            Task(id="T001", description="Task 1", parallel=True),
            Task(id="T002", description="Task 2", parallel=True, dependencies=[Dependency(task_id="T001")]),
            Task(id="T003", description="Task 3", parallel=False),
        ]

        analyzer = DependencyAnalyzer(tasks)
        groups = analyzer.get_parallel_groups()

        # T001 and T002 are in different levels
        assert len(groups) >= 1

    def test_get_parallel_groups_no_parallel_tasks(self) -> None:
        """验证无并行任务时的分组"""
        tasks = [
            Task(id="T001", description="Task 1", parallel=False),
            Task(id="T002", description="Task 2", parallel=False),
        ]

        analyzer = DependencyAnalyzer(tasks)
        groups = analyzer.get_parallel_groups()

        # No parallel groups
        assert len(groups) == 0


class TestExecutionLevelCalculation:
    """Test execution level calculation."""

    def test_execution_levels_linear(self) -> None:
        """验证线性任务的执行层级"""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T001")]),
            Task(id="T003", description="Task 3", dependencies=[Dependency(task_id="T002")]),
        ]

        analyzer = DependencyAnalyzer(tasks)
        levels = analyzer.get_execution_levels()

        assert 0 in levels and len(levels[0]) == 1
        assert 1 in levels and len(levels[1]) == 1
        assert 2 in levels and len(levels[2]) == 1

        # Verify task IDs at each level
        assert levels[0][0].id == "T001"
        assert levels[1][0].id == "T002"
        assert levels[2][0].id == "T003"

    def test_execution_levels_diamond(self) -> None:
        """验证菱形依赖的执行层级"""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T001")]),
            Task(id="T003", description="Task 3", dependencies=[Dependency(task_id="T001")]),
            Task(
                id="T004",
                description="Task 4",
                dependencies=[Dependency(task_id="T002"), Dependency(task_id="T003")],
            ),
        ]

        analyzer = DependencyAnalyzer(tasks)
        levels = analyzer.get_execution_levels()

        # Level 0: T001
        # Level 1: T002, T003
        # Level 2: T004
        assert 0 in levels and any(t.id == "T001" for t in levels[0])
        assert 1 in levels and len(levels[1]) == 2
        assert 2 in levels and any(t.id == "T004" for t in levels[2])

    def test_execution_levels_no_dependencies(self) -> None:
        """验证无依赖任务的执行层级"""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2"),
            Task(id="T003", description="Task 3"),
        ]

        analyzer = DependencyAnalyzer(tasks)
        levels = analyzer.get_execution_levels()

        # All at level 0
        assert 0 in levels and len(levels[0]) == 3
        assert len(levels) == 1  # Only level 0 exists


class TestDependencyValidation:
    """Test dependency validation."""

    def test_validate_dependencies_all_valid(self) -> None:
        """验证所有依赖都有效"""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T001")]),
        ]

        analyzer = DependencyAnalyzer(tasks)
        missing = analyzer.validate_dependencies()

        assert len(missing) == 0

    def test_validate_dependencies_missing_target(self) -> None:
        """验证缺失依赖目标"""
        tasks = [
            Task(id="T001", description="Task 1", dependencies=[Dependency(task_id="T999")]),
        ]

        analyzer = DependencyAnalyzer(tasks)
        missing = analyzer.validate_dependencies()

        assert len(missing) == 1
        assert "T001 -> T999" in missing[0]

    def test_validate_dependencies_multiple_missing(self) -> None:
        """验证多个缺失依赖"""
        tasks = [
            Task(id="T001", description="Task 1", dependencies=[Dependency(task_id="T999"), Dependency(task_id="T888")]),
        ]

        analyzer = DependencyAnalyzer(tasks)
        missing = analyzer.validate_dependencies()

        assert len(missing) == 2


class TestTableDrivenAnalysis:
    """Table-driven tests for dependency analysis (TDD requirement)."""

    @pytest.mark.parametrize(
        "tasks_dict,expected_error,expected_order",
        [
            # Linear chain - no error
            (
                {"T001": [], "T002": ["T001"], "T003": ["T002"]},
                None,
                ["T001", "T002", "T003"],
            ),
            # Diamond - no error, T004 last
            (
                {"T001": [], "T002": ["T001"], "T003": ["T001"], "T004": ["T002", "T003"]},
                None,
                None,  # Don't check exact order, just no error
            ),
            # Simple cycle - error
            ({"T001": ["T002"], "T002": ["T001"]}, CircularDependencyError, None),
            # Self-reference - error
            ({"T001": ["T001"]}, CircularDependencyError, None),
            # Complex cycle - error
            ({"T001": ["T002"], "T002": ["T003"], "T003": ["T001"]}, CircularDependencyError, None),
        ],
    )
    def test_topological_sort_table_driven(
        self, tasks_dict: Dict[str, List[str]], expected_error: Any, expected_order: Any
    ) -> None:
        """表格驱动测试：拓扑排序"""
        tasks = [
            Task(id=tid, description=f"Task {tid}", dependencies=[Dependency(task_id=d) for d in deps])
            for tid, deps in tasks_dict.items()
        ]

        analyzer = DependencyAnalyzer(tasks)

        if expected_error is None:
            # Should succeed
            sorted_tasks = analyzer.topological_sort()
            assert len(sorted_tasks) == len(tasks)
            if expected_order:
                assert [t.id for t in sorted_tasks] == expected_order
        else:
            # Should raise expected error
            with pytest.raises(expected_error):
                analyzer.topological_sort()
