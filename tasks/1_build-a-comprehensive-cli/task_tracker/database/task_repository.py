"""Task repository for database operations."""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from task_tracker.models import Task, TaskStatus, TaskPriority
from task_tracker.database.connection import Database


class TaskRepository:
    """
    Repository for task CRUD operations.

    Provides methods for creating, reading, updating, and deleting tasks
    in the database.
    """

    def __init__(self, database: Database):
        """
        Initialize task repository.

        Args:
            database: Database connection instance
        """
        self.db = database

    def create(self, task: Task) -> Task:
        """
        Create a new task in the database.

        Args:
            task: Task object to create

        Returns:
            Task: Created task with assigned ID
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (
                    title, description, status, priority, tags,
                    created_at, updated_at, started_at, completed_at,
                    estimated_time, actual_time, metadata, parent_id, project, assignee
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.title,
                    task.description,
                    task.status.value,
                    task.priority.value,
                    json.dumps(task.tags),
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.estimated_time,
                    task.actual_time,
                    json.dumps(task.metadata),
                    task.parent_id,
                    task.project,
                    task.assignee,
                ),
            )
            task.id = cursor.lastrowid
            return task

    def get_by_id(self, task_id: int) -> Optional[Task]:
        """
        Retrieve a task by ID.

        Args:
            task_id: Task ID to retrieve

        Returns:
            Task if found, None otherwise
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_task(row)
            return None

    def get_all(self) -> List[Task]:
        """
        Retrieve all tasks.

        Returns:
            List of all tasks
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
            return [self._row_to_task(row) for row in cursor.fetchall()]

    def get_by_status(self, status: TaskStatus) -> List[Task]:
        """
        Retrieve tasks by status.

        Args:
            status: Task status to filter by

        Returns:
            List of tasks with specified status
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
                (status.value,)
            )
            return [self._row_to_task(row) for row in cursor.fetchall()]

    def get_by_project(self, project: str) -> List[Task]:
        """
        Retrieve tasks by project.

        Args:
            project: Project name to filter by

        Returns:
            List of tasks in specified project
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE project = ? ORDER BY created_at DESC",
                (project,)
            )
            return [self._row_to_task(row) for row in cursor.fetchall()]

    def get_by_tag(self, tag: str) -> List[Task]:
        """
        Retrieve tasks by tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of tasks with specified tag
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE tags LIKE ?", (f"%{tag}%",))
            return [self._row_to_task(row) for row in cursor.fetchall()]

    def update(self, task: Task) -> Task:
        """
        Update an existing task.

        Args:
            task: Task object with updated values

        Returns:
            Updated task
        """
        task.updated_at = datetime.now()
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE tasks SET
                    title = ?, description = ?, status = ?, priority = ?,
                    tags = ?, updated_at = ?, started_at = ?, completed_at = ?,
                    estimated_time = ?, actual_time = ?, metadata = ?,
                    parent_id = ?, project = ?, assignee = ?
                WHERE id = ?
                """,
                (
                    task.title,
                    task.description,
                    task.status.value,
                    task.priority.value,
                    json.dumps(task.tags),
                    task.updated_at.isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.estimated_time,
                    task.actual_time,
                    json.dumps(task.metadata),
                    task.parent_id,
                    task.project,
                    task.assignee,
                    task.id,
                ),
            )
            return task

    def delete(self, task_id: int) -> bool:
        """
        Delete a task by ID.

        Args:
            task_id: ID of task to delete

        Returns:
            True if deleted, False if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    def search(self, query: str) -> List[Task]:
        """
        Search tasks by title or description.

        Args:
            query: Search query string

        Returns:
            List of matching tasks
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM tasks
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY created_at DESC
                """,
                (f"%{query}%", f"%{query}%")
            )
            return [self._row_to_task(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get task statistics.

        Returns:
            Dictionary with task statistics
        """
        with self.db.get_connection() as conn:
            # Total tasks
            cursor = conn.execute("SELECT COUNT(*) FROM tasks")
            total = cursor.fetchone()[0]

            # Tasks by status
            cursor = conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
            by_status = {row[0]: row[1] for row in cursor.fetchall()}

            # Tasks by priority
            cursor = conn.execute("SELECT priority, COUNT(*) FROM tasks GROUP BY priority")
            by_priority = {row[0]: row[1] for row in cursor.fetchall()}

            # Average completion time
            cursor = conn.execute("""
                SELECT AVG(julianday(completed_at) - julianday(started_at)) * 24 * 60
                FROM tasks
                WHERE completed_at IS NOT NULL AND started_at IS NOT NULL
            """)
            avg_completion = cursor.fetchone()[0] or 0

            return {
                "total": total,
                "by_status": by_status,
                "by_priority": by_priority,
                "avg_completion_time_minutes": round(avg_completion, 2),
            }

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object."""
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            status=TaskStatus(row["status"]),
            priority=TaskPriority(row["priority"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            estimated_time=row["estimated_time"],
            actual_time=row["actual_time"] or 0,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            parent_id=row["parent_id"],
            project=row["project"],
            assignee=row["assignee"],
        )
