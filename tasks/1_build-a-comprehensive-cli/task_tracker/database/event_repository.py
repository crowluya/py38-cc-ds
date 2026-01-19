"""Event repository for tracking task history."""

import json
from typing import List, Optional
from datetime import datetime

from task_tracker.models import Event, EventType
from task_tracker.database.connection import Database


class EventRepository:
    """
    Repository for event tracking operations.

    Provides methods for creating and retrieving events
    that track task state changes over time.
    """

    def __init__(self, database: Database):
        """
        Initialize event repository.

        Args:
            database: Database connection instance
        """
        self.db = database

    def create(self, event: Event) -> Event:
        """
        Create a new event in the database.

        Args:
            event: Event object to create

        Returns:
            Event: Created event with assigned ID
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    task_id, event_type, timestamp, old_value, new_value, metadata, user
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.task_id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.old_value,
                    event.new_value,
                    json.dumps(event.metadata),
                    event.user,
                ),
            )
            event.id = cursor.lastrowid
            return event

    def get_by_task_id(self, task_id: int) -> List[Event]:
        """
        Retrieve all events for a specific task.

        Args:
            task_id: Task ID to get events for

        Returns:
            List of events for the task, ordered by timestamp
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE task_id = ?
                ORDER BY timestamp ASC
                """,
                (task_id,)
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_by_type(self, event_type: EventType) -> List[Event]:
        """
        Retrieve events by type.

        Args:
            event_type: Type of event to filter by

        Returns:
            List of events of specified type
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE event_type = ?
                ORDER BY timestamp DESC
                """,
                (event_type.value,)
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 50) -> List[Event]:
        """
        Retrieve most recent events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent events
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_events_in_range(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """
        Retrieve events within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of events within the range
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
                """,
                (start_date.isoformat(), end_date.isoformat())
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def delete_by_task_id(self, task_id: int) -> int:
        """
        Delete all events for a specific task.

        Args:
            task_id: Task ID to delete events for

        Returns:
            Number of events deleted
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM events WHERE task_id = ?", (task_id,))
            return cursor.rowcount

    def _row_to_event(self, row) -> Event:
        """Convert database row to Event object."""
        return Event(
            id=row["id"],
            task_id=row["task_id"],
            event_type=EventType(row["event_type"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            old_value=row["old_value"],
            new_value=row["new_value"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            user=row["user"],
        )
