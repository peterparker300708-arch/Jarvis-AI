"""SQLAlchemy ORM models for the Jarvis AI database."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


class Command(Base):
    """Stores every command received by Jarvis and its response."""

    __tablename__ = "commands"

    command_id = Column(Integer, primary_key=True, autoincrement=True)
    command_text = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    success = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Command id={self.command_id} success={self.success}>"

    def to_dict(self) -> dict:
        return {
            "command_id": self.command_id,
            "command_text": self.command_text,
            "response": self.response,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "success": self.success,
        }


class UserPreference(Base):
    """Key/value store for user preferences."""

    __tablename__ = "user_preferences"

    key = Column(String(256), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow(), nullable=False)

    def __repr__(self) -> str:
        return f"<UserPreference key={self.key!r}>"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Note(Base):
    """User notes with optional tags."""

    __tablename__ = "notes"

    note_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=True)
    tags = Column(String(1024), nullable=True, default="")
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow(), nullable=False)

    def __repr__(self) -> str:
        return f"<Note id={self.note_id} title={self.title!r}>"

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Reminder(Base):
    """Time-based reminders."""

    __tablename__ = "reminders"

    reminder_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(512), nullable=False)
    message = Column(Text, nullable=True)
    remind_at = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)

    def __repr__(self) -> str:
        return f"<Reminder id={self.reminder_id} title={self.title!r} completed={self.completed}>"

    def to_dict(self) -> dict:
        return {
            "reminder_id": self.reminder_id,
            "title": self.title,
            "message": self.message,
            "remind_at": self.remind_at.isoformat() if self.remind_at else None,
            "completed": self.completed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Task(Base):
    """Scheduled background tasks managed by the task scheduler."""

    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False, unique=True)
    schedule = Column(String(256), nullable=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Task id={self.task_id} name={self.name!r} active={self.active}>"

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "schedule": self.schedule,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "active": self.active,
        }


class ActivityLog(Base):
    """Audit log for all significant actions taken by or in Jarvis."""

    __tablename__ = "activity_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(256), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    user = Column(String(256), nullable=True, default="system")

    def __repr__(self) -> str:
        return f"<ActivityLog id={self.log_id} action={self.action!r}>"

    def to_dict(self) -> dict:
        return {
            "log_id": self.log_id,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user": self.user,
        }


def create_all_tables(engine) -> None:
    """Create all tables in the database if they do not already exist.

    Args:
        engine: SQLAlchemy engine instance.
    """
    Base.metadata.create_all(engine)
