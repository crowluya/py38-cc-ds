"""Database connection and initialization."""

import os
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


class Database:
    """
    Database connection manager for task tracking.

    Handles SQLite database initialization, connection management,
    and schema creation.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to database file. If None, uses default location.
        """
        if db_path is None:
            # Default to data directory in user's home
            data_dir = Path.home() / ".task_tracker"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "tasks.db")

        self.db_path = db_path
        self._ensure_database_exists()

    def _ensure_database_exists(self):
        """Create database file and directory if they don't exist."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """
        Get database connection with context manager.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_schema(self):
        """Create database tables if they don't exist."""
        with self.get_connection() as conn:
            # Tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    tags TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    estimated_time INTEGER,
                    actual_time INTEGER NOT NULL DEFAULT 0,
                    metadata TEXT,
                    parent_id INTEGER,
                    project TEXT,
                    assignee TEXT,
                    FOREIGN KEY (parent_id) REFERENCES tasks(id)
                )
            """)

            # Events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    old_value TEXT,
                    new_value TEXT,
                    metadata TEXT,
                    user TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            # Time entries table for tracking work sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS time_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration INTEGER,
                    notes TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            # Create indexes for better query performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_project
                ON tasks(project)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_task_id
                ON events(task_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_time_entries_task_id
                ON time_entries(task_id)
            """)

    def backup_database(self, backup_path: str):
        """
        Create a backup of the database.

        Args:
            backup_path: Path where backup should be saved
        """
        import shutil
        Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db_path, backup_path)

    def restore_database(self, backup_path: str):
        """
        Restore database from backup.

        Args:
            backup_path: Path to backup file
        """
        import shutil
        shutil.copy2(backup_path, self.db_path)

    def get_database_size(self) -> int:
        """
        Get database file size in bytes.

        Returns:
            int: Size of database file in bytes
        """
        return os.path.getsize(self.db_path)

    def export_to_json(self, output_path: str):
        """
        Export all data to JSON file.

        Args:
            output_path: Path where JSON file should be saved
        """
        import json
        from datetime import datetime

        data = {"tasks": [], "events": [], "time_entries": [], "exported_at": datetime.now().isoformat()}

        with self.get_connection() as conn:
            # Export tasks
            cursor = conn.execute("SELECT * FROM tasks")
            for row in cursor.fetchall():
                data["tasks"].append(dict(row))

            # Export events
            cursor = conn.execute("SELECT * FROM events")
            for row in cursor.fetchall():
                data["events"].append(dict(row))

            # Export time entries
            cursor = conn.execute("SELECT * FROM time_entries")
            for row in cursor.fetchall():
                data["time_entries"].append(dict(row))

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def import_from_json(self, input_path: str):
        """
        Import data from JSON file.

        Args:
            input_path: Path to JSON file to import
        """
        import json

        with open(input_path, "r") as f:
            data = json.load(f)

        with self.get_connection() as conn:
            # Clear existing data
            conn.execute("DELETE FROM time_entries")
            conn.execute("DELETE FROM events")
            conn.execute("DELETE FROM tasks")

            # Import tasks
            for task in data.get("tasks", []):
                columns = ", ".join(task.keys())
                placeholders = ", ".join(["?" for _ in task])
                conn.execute(f"INSERT INTO tasks ({columns}) VALUES ({placeholders})", list(task.values()))

            # Import events
            for event in data.get("events", []):
                columns = ", ".join(event.keys())
                placeholders = ", ".join(["?" for _ in event])
                conn.execute(f"INSERT INTO events ({columns}) VALUES ({placeholders})", list(event.values()))

            # Import time entries
            for entry in data.get("time_entries", []):
                columns = ", ".join(entry.keys())
                placeholders = ", ".join(["?" for _ in entry])
                conn.execute(f"INSERT INTO time_entries ({columns}) VALUES ({placeholders})", list(entry.values()))
