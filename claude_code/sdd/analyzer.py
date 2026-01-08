"""
SDD Dependency Analyzer - Topological sort and cycle detection.

Python 3.8.10 compatible
Implements:
- Topological sorting of tasks based on dependencies
- Circular dependency detection
- Parallel execution group identification
- Execution level calculation
"""

from __future__ import annotations

from typing import Dict, List, Set

from claude_code.sdd.models import Task


class CircularDependencyError(Exception):
    """Exception raised when circular dependencies are detected."""

    def __init__(self, cycle: List[str]):
        """
        Initialize with the detected cycle.

        Args:
            cycle: List of task IDs forming the cycle
        """
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class DependencyAnalyzer:
    """
    Analyzes task dependencies and provides execution ordering.

    Features:
    - Topological sorting for linear execution order
    - Circular dependency detection
    - Parallel group identification
    - Execution level calculation
    """

    def __init__(self, tasks: List[Task]):
        """
        Initialize analyzer with task list.

        Args:
            tasks: List of tasks to analyze
        """
        self.tasks = tasks
        self._task_map: Dict[str, Task] = {task.id: task for task in tasks}

    def topological_sort(self) -> List[Task]:
        """
        Perform topological sort on tasks.

        Returns:
            List of tasks in dependency order (dependencies before dependents)

        Raises:
            CircularDependencyError: If circular dependencies are detected
        """
        # Build adjacency list and in-degree count
        in_degree: Dict[str, int] = {task.id: 0 for task in self.tasks}
        adj_list: Dict[str, List[str]] = {task.id: [] for task in self.tasks}

        for task in self.tasks:
            for dep in task.dependencies:
                dep_id = dep.task_id
                if dep_id in adj_list:
                    adj_list[dep_id].append(task.id)
                    in_degree[task.id] += 1

        # Kahn's algorithm
        queue: List[str] = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result: List[Task] = []
        visited: Set[str] = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue

            visited.add(current)
            result.append(self._task_map[current])

            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(result) != len(self.tasks):
            # Find cycle
            cycle = self._find_cycle()
            raise CircularDependencyError(cycle)

        return result

    def _find_cycle(self) -> List[str]:
        """
        Find a cycle in the dependency graph using DFS.

        Returns:
            List of task IDs forming a cycle
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycle_path: List[str] = []

        def dfs(node: str, path: List[str]) -> bool:
            """DFS helper to find cycle."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            task = self._task_map.get(node)
            if task:
                for dep in task.dependencies:
                    dep_id = dep.task_id
                    if dep_id not in visited:
                        if dfs(dep_id, path):
                            return True
                    elif dep_id in rec_stack:
                        # Found cycle - capture it
                        cycle_start = path.index(dep_id)
                        cycle_path.extend(path[cycle_start:] + [dep_id])
                        return True

            path.pop()
            rec_stack.remove(node)
            return False

        for task_id in self._task_map:
            if task_id not in visited:
                if dfs(task_id, []):
                    return cycle_path

        return []

    def get_parallel_groups(self) -> List[List[Task]]:
        """
        Group tasks that can be executed in parallel.

        Tasks can be parallel if:
        1. They are marked as parallel=True
        2. They have no dependencies between them
        3. They are at the same execution level

        Returns:
            List of groups, where each group contains tasks that can run in parallel
        """
        levels = self.get_execution_levels()
        groups: List[List[Task]] = []

        for level_tasks in levels.values():
            # Filter only parallel-capable tasks
            parallel_tasks = [t for t in level_tasks if t.parallel]

            if parallel_tasks:
                groups.append(parallel_tasks)

        return groups

    def get_execution_levels(self) -> Dict[int, List[Task]]:
        """
        Calculate execution levels for tasks.

        Level 0: Tasks with no dependencies
        Level 1: Tasks that depend only on Level 0 tasks
        Level N: Tasks that depend only on tasks from levels < N

        Returns:
            Dict mapping level number to list of tasks at that level
        """
        levels: Dict[int, List[Task]] = {}
        task_level: Dict[str, int] = {}

        # Initialize all tasks at level -1 (unvisited)
        for task in self.tasks:
            task_level[task.id] = -1

        def calculate_level(task_id: str) -> int:
            """Recursively calculate task level."""
            if task_level[task_id] >= 0:
                return task_level[task_id]

            task = self._task_map.get(task_id)
            if not task or not task.dependencies:
                task_level[task_id] = 0
                return 0

            max_dep_level = -1
            for dep in task.dependencies:
                dep_id = dep.task_id
                if dep_id in self._task_map:
                    dep_level = calculate_level(dep_id)
                    max_dep_level = max(max_dep_level, dep_level)

            task_level[task_id] = max_dep_level + 1
            return task_level[task_id]

        # Calculate level for each task
        for task in self.tasks:
            calculate_level(task.id)

        # Group by level
        for task in self.tasks:
            level = task_level[task.id]
            if level not in levels:
                levels[level] = []
            levels[level].append(task)

        return levels

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect all circular dependencies in the task graph.

        Returns:
            List of cycles (each cycle is a list of task IDs)
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            """DFS to find all cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            task = self._task_map.get(node)
            if task:
                for dep in task.dependencies:
                    dep_id = dep.task_id
                    if dep_id not in visited:
                        dfs(dep_id, path)
                    elif dep_id in rec_stack:
                        # Found cycle
                        cycle_start = path.index(dep_id)
                        cycle = path[cycle_start:] + [dep_id]
                        if cycle not in cycles:
                            cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for task_id in self._task_map:
            if task_id not in visited:
                dfs(task_id, [])

        return cycles

    def validate_dependencies(self) -> List[str]:
        """
        Validate that all task dependencies exist.

        Returns:
            List of missing dependency IDs
        """
        missing: List[str] = []
        all_task_ids = set(self._task_map.keys())

        for task in self.tasks:
            for dep in task.dependencies:
                if dep.task_id not in all_task_ids:
                    missing.append(f"{task.id} -> {dep.task_id}")

        return missing
