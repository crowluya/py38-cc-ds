"""Database models and storage layer."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from ai_command_palette.storage.config import Config

Base = declarative_base()


class CommandUsage(Base):
    """Track command execution history."""

    __tablename__ = "command_usage"

    id = Integer(primary_key=True)
    command = String(500, nullable=False, index=True)
    command_type = String(50, nullable=False)  # 'system', 'note', 'file', 'workflow'
    args = Text, nullable=True  # JSON encoded arguments
    timestamp = DateTime, default=datetime.utcnow, index=True
    exit_code = Integer, nullable=True
    duration_ms = Integer, nullable=True

    # Context information
    working_dir = String(1000), nullable=True
    git_branch = String(500), nullable=True

    # Scoring data
    success = Boolean, default=True


class FileUsage(Base):
    """Track file access patterns."""

    __tablename__ = "file_usage"

    id = Integer(primary_key=True)
    file_path = String(2000, nullable=False, index=True)
    action = String(50, nullable=False)  # 'open', 'edit', 'create', 'delete'
    timestamp = DateTime, default=datetime.utcnow, index=True

    # Context
    working_dir = String(1000), nullable=True
    file_type = String(100), nullable=True


class SuggestionFeedback(Base):
    """Track user feedback on suggestions."""

    __tablename__ = "suggestion_feedback"

    id = Integer(primary_key=True)
    suggestion = String(500, nullable=False)
    accepted = Boolean, nullable=False
    position_in_list = Integer, nullable=True
    timestamp = DateTime, default=datetime.utcnow


class Pattern(Base):
    """Store learned patterns for recommendations."""

    __tablename__ = "patterns"

    id = Integer(primary_key=True)
    pattern_type = String(50, nullable=False)  # 'time_of_day', 'dir_context', 'sequence'
    pattern_data = Text, nullable=False  # JSON encoded pattern data
    confidence = Float, default=0.0
    last_seen = DateTime, default=datetime.utcnow
    usage_count = Integer, default=1


class Database:
    """Database manager for AI Command Palette."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize database connection."""
        self.config = config or Config()
        self.db_path = self.config.data_dir / "usage.db"

        # Create engine with connection pooling
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Initialize schema
        self._init_db()

    def _init_db(self):
        """Create database tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def log_command(
        self,
        command: str,
        command_type: str,
        args: Optional[str] = None,
        exit_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        working_dir: Optional[str] = None,
        git_branch: Optional[str] = None,
        success: bool = True,
    ) -> CommandUsage:
        """Log a command execution."""
        session = self.get_session()
        try:
            usage = CommandUsage(
                command=command,
                command_type=command_type,
                args=args,
                exit_code=exit_code,
                duration_ms=duration_ms,
                working_dir=working_dir,
                git_branch=git_branch,
                success=success,
            )
            session.add(usage)
            session.commit()
            session.refresh(usage)
            return usage
        finally:
            session.close()

    def log_file_access(
        self,
        file_path: str,
        action: str,
        working_dir: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> FileUsage:
        """Log a file access event."""
        session = self.get_session()
        try:
            usage = FileUsage(
                file_path=file_path,
                action=action,
                working_dir=working_dir,
                file_type=file_type,
            )
            session.add(usage)
            session.commit()
            session.refresh(usage)
            return usage
        finally:
            session.close()

    def log_feedback(self, suggestion: str, accepted: bool, position: Optional[int] = None):
        """Log user feedback on a suggestion."""
        session = self.get_session()
        try:
            feedback = SuggestionFeedback(
                suggestion=suggestion, accepted=accepted, position_in_list=position
            )
            session.add(feedback)
            session.commit()
        finally:
            session.close()

    def get_command_frequency(
        self, command_type: Optional[str] = None, days: int = 30
    ) -> dict[str, int]:
        """Get command frequency statistics."""
        session = self.get_session()
        try:
            query = session.query(
                CommandUsage.command, func.count(CommandUsage.id).label("count")
            )

            if command_type:
                query = query.filter(CommandUsage.command_type == command_type)

            # Filter by date range
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(CommandUsage.timestamp >= cutoff_date)

            results = query.group_by(CommandUsage.command).order_by(
                func.count(CommandUsage.id).desc()
            )

            return {row.command: row.count for row in results.all()}
        finally:
            session.close()

    def get_recent_commands(self, limit: int = 50) -> list[CommandUsage]:
        """Get recently executed commands."""
        session = self.get_session()
        try:
            return (
                session.query(CommandUsage)
                .order_by(CommandUsage.timestamp.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    def cleanup_old_data(self, retention_days: int = 90):
        """Remove data older than retention period."""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            # Delete old command usage
            session.query(CommandUsage).filter(CommandUsage.timestamp < cutoff_date).delete()

            # Delete old file usage
            session.query(FileUsage).filter(FileUsage.timestamp < cutoff_date).delete()

            # Delete old feedback
            session.query(SuggestionFeedback).filter(
                SuggestionFeedback.timestamp < cutoff_date
            ).delete()

            session.commit()
        finally:
            session.close()

    def get_usage_stats(self) -> dict:
        """Get overall usage statistics."""
        session = self.get_session()
        try:
            total_commands = session.query(func.count(CommandUsage.id)).scalar()
            total_files = session.query(func.count(FileUsage.id)).scalar()

            # Most common command types
            command_types = (
                session.query(
                    CommandUsage.command_type, func.count(CommandUsage.id).label("count")
                )
                .group_by(CommandUsage.command_type)
                .all()
            )

            return {
                "total_commands": total_commands,
                "total_files": total_files,
                "command_types": {ct: count for ct, count in command_types},
            }
        finally:
            session.close()
