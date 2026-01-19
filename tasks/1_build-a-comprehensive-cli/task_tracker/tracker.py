"""Task tracking service for managing tasks and events."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from task_tracker.models import Task, TaskStatus, Event, EventType
from task_tracker.database import Database, TaskRepository, EventRepository


class TaskTracker:
    """
    Main service for task tracking operations.

    Provides high-level methods for managing tasks and tracking
    their lifecycle with automatic event logging.
    """

    def __init__(self, database: Optional[Database] = None):
        """
        Initialize task tracker.

        Args:
            database: Database instance. If None, creates default.
        """
        self.db = database or Database()
        self.db.initialize_schema()
        self.task_repo = TaskRepository(self.db)
        self.event_repo = EventRepository(self.db)

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        tags: Optional[List[str]] = None,
        project: Optional[str] = None,
        estimated_time: Optional[int] = None,
        assignee: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            title: Task title
            description: Task description
            priority: Task priority (low, medium, high, critical)
            tags: List of tags
            project: Project name
            estimated_time: Estimated time in minutes
            assignee: Task assignee
            metadata: Additional metadata

        Returns:
            Created task
        """
        task = Task(
            title=title,
            description=description,
            priority=priority,
            tags=tags or [],
            project=project,
            estimated_time=estimated_time,
            assignee=assignee,
            metadata=metadata or {},
        )

        created_task = self.task_repo.create(task)

        # Log creation event
        self._log_event(
            created_task.id,
            EventType.CREATED,
            new_value=f"Task created: {title}",
        )

        return created_task

    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        tags: Optional[List[str]] = None,
        project: Optional[str] = None,
        estimated_time: Optional[int] = None,
        assignee: Optional[str] = None,
    ) -> Optional[Task]:
        """
        Update an existing task.

        Args:
            task_id: ID of task to update
            title: New title
            description: New description
            priority: New priority
            tags: New list of tags
            project: New project
            estimated_time: New estimated time
            assignee: New assignee

        Returns:
            Updated task or None if not found
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None

        # Track changes
        changes = []
        if title and task.title != title:
            changes.append(("title", task.title, title))
            task.title = title
        if description is not None and task.description != description:
            changes.append(("description", task.description, description))
            task.description = description
        if priority and task.priority != priority:
            changes.append(("priority", task.priority.value, priority))
            task.priority = priority
        if tags is not None and task.tags != tags:
            changes.append(("tags", str(task.tags), str(tags)))
            task.tags = tags
        if project is not None and task.project != project:
            changes.append(("project", task.project, project))
            task.project = project
        if estimated_time is not None and task.estimated_time != estimated_time:
            changes.append(("estimated_time", task.estimated_time, estimated_time))
            task.estimated_time = estimated_time
        if assignee is not None and task.assignee != assignee:
            changes.append(("assignee", task.assignee, assignee))
            task.assignee = assignee

        if changes:
            updated_task = self.task_repo.update(task)

            # Log update event
            for field, old_val, new_val in changes:
                self._log_event(
                    task_id,
                    EventType.UPDATED,
                    old_value=str(old_val) if old_val else None,
                    new_value=str(new_val) if new_val else None,
                    metadata={"field": field},
                )

            return updated_task

        return task

    def start_task(self, task_id: int) -> Optional[Task]:
        """
        Start working on a task.

        Args:
            task_id: ID of task to start

        Returns:
            Updated task or None if not found
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None

        if task.status == TaskStatus.IN_PROGRESS:
            return task  # Already started

        task.status = TaskStatus.IN_PROGRESS
        if not task.started_at:
            task.started_at = datetime.now()

        updated_task = self.task_repo.update(task)

        # Log start event
        self._log_event(task_id, EventType.STARTED)

        return updated_task

    def pause_task(self, task_id: int) -> Optional[Task]:
        """
        Pause work on a task.

        Args:
            task_id: ID of task to pause

        Returns:
            Updated task or None if not found
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None

        if task.status != TaskStatus.IN_PROGRESS:
            return task

        task.status = TaskStatus.PAUSED
        updated_task = self.task_repo.update(task)

        # Log pause event
        self._log_event(task_id, EventType.PAUSED)

        return updated_task

    def resume_task(self, task_id: int) -> Optional[Task]:
        """
        Resume work on a paused task.

        Args:
            task_id: ID of task to resume

        Returns:
            Updated task or None if not found
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None

        if task.status != TaskStatus.PAUSED:
            return task

        task.status = TaskStatus.IN_PROGRESS
        updated_task = self.task_repo.update(task)

        # Log resume event
        self._log_event(task_id, EventType.RESUMED)

        return updated_task

    def complete_task(self, task_id: int, actual_time: Optional[int] = None) -> Optional[Task]:
        """
        Mark a task as completed.

        Args:
            task_id: ID of task to complete
            actual_time: Actual time spent in minutes

        Returns:
            Updated task or None if not found
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None

        old_status = task.status.value
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()

        if actual_time is not None:
            task.actual_time = actual_time

        updated_task = self.task_repo.update(task)

        # Log completion event
        self._log_event(
            task_id,
            EventType.COMPLETED,
            old_value=old_status,
            new_value="completed",
        )

        return updated_task

    def cancel_task(self, task_id: int) -> Optional[Task]:
        """
        Cancel a task.

        Args:
            task_id: ID of task to cancel

        Returns:
            Updated task or None if not found
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None

        task.status = TaskStatus.CANCELLED
        updated_task = self.task_repo.update(task)

        # Log cancellation event
        self._log_event(task_id, EventType.CANCELLED)

        return updated_task

    def delete_task(self, task_id: int) -> bool:
        """
        Delete a task and all its events.

        Args:
            task_id: ID of task to delete

        Returns:
            True if deleted, False if not found
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return False

        # Delete events first
        self.event_repo.delete_by_task_id(task_id)

        # Delete task
        return self.task_repo.delete(task_id)

    def get_task(self, task_id: int) -> Optional[Task]:
        """
        Retrieve a task by ID.

        Args:
            task_id: ID of task to retrieve

        Returns:
            Task or None if not found
        """
        return self.task_repo.get_by_id(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        project: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Task]:
        """
        List tasks with optional filtering.

        Args:
            status: Filter by status
            project: Filter by project
            tag: Filter by tag
            search: Search in title and description

        Returns:
            List of matching tasks
        """
        if status:
            return self.task_repo.get_by_status(TaskStatus(status))
        elif project:
            return self.task_repo.get_by_project(project)
        elif tag:
            return self.task_repo.get_by_tag(tag)
        elif search:
            return self.task_repo.search(search)
        else:
            return self.task_repo.get_all()

    def get_task_history(self, task_id: int) -> List[Event]:
        """
        Get event history for a task.

        Args:
            task_id: ID of task

        Returns:
            List of events for the task
        """
        return self.event_repo.get_by_task_id(task_id)

    def add_time_entry(
        self,
        task_id: int,
        duration: int,
        notes: Optional[str] = None,
    ) -> Optional[Task]:
        """
        Add time entry to a task.

        Args:
            task_id: ID of task
            duration: Duration in minutes
            notes: Optional notes

        Returns:
            Updated task or None if not found
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None

        # Update actual time
        task.actual_time += duration
        updated_task = self.task_repo.update(task)

        # Log time entry event
        self._log_event(
            task_id,
            EventType.TIME_LOGGED,
            new_value=f"{duration} minutes",
            metadata={"notes": notes, "duration": duration},
        )

        return updated_task

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics.

        Returns:
            Dictionary with statistics
        """
        return self.task_repo.get_statistics()

    def _log_event(
        self,
        task_id: int,
        event_type: EventType,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an event for a task.

        Args:
            task_id: ID of task
            event_type: Type of event
            old_value: Old value (for changes)
            new_value: New value (for changes)
            metadata: Additional metadata
        """
        event = Event(
            task_id=task_id,
            event_type=event_type,
            timestamp=datetime.now(),
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
        )
        self.event_repo.create(event)
