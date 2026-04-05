"""Database manager providing CRUD operations for all Jarvis models."""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker, Session

from .models import (
    ActivityLog,
    Base,
    Command,
    Note,
    Reminder,
    Task,
    UserPreference,
    create_all_tables,
)


_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "jarvis.db"
)


class DatabaseManager:
    """Thread-safe SQLite database manager for the Jarvis AI system.

    All public methods are safe to call from multiple threads simultaneously.

    Args:
        db_path: Filesystem path for the SQLite database file.
        echo: If ``True`` SQLAlchemy will log all SQL statements.
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH, echo: bool = False) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            echo=echo,
            connect_args={"check_same_thread": False},
        )
        create_all_tables(self._engine)
        self._Session = sessionmaker(bind=self._engine, expire_on_commit=False)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Context-manager session helper
    # ------------------------------------------------------------------

    def _session(self) -> Session:
        return self._Session()

    # ------------------------------------------------------------------
    # Command log
    # ------------------------------------------------------------------

    def log_command(
        self,
        text: str,
        response: str = "",
        success: bool = True,
    ) -> Command:
        """Insert a new command record.

        Args:
            text: Raw command text received from user or voice.
            response: Generated response string.
            success: Whether the command was handled successfully.

        Returns:
            The persisted :class:`~database.models.Command` instance.
        """
        with self._lock, self._session() as session:
            cmd = Command(command_text=text, response=response, success=success)
            session.add(cmd)
            session.commit()
            return cmd

    def get_recent_commands(self, limit: int = 50) -> List[dict]:
        """Return the *limit* most recent command records as dicts."""
        with self._session() as session:
            rows = (
                session.query(Command)
                .order_by(Command.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [r.to_dict() for r in rows]

    # ------------------------------------------------------------------
    # User preferences
    # ------------------------------------------------------------------

    def save_preference(self, key: str, value: Any) -> None:
        """Upsert a user preference.

        Args:
            key: Preference key.
            value: Preference value; will be cast to ``str`` for storage.
        """
        with self._lock, self._session() as session:
            pref = session.get(UserPreference, key)
            str_value = str(value) if value is not None else None
            if pref is None:
                pref = UserPreference(key=key, value=str_value)
                session.add(pref)
            else:
                pref.value = str_value
                pref.updated_at = datetime.utcnow()
            session.commit()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a stored preference value.

        Args:
            key: Preference key.
            default: Value returned when the key does not exist.

        Returns:
            Stored value string, or *default*.
        """
        with self._session() as session:
            pref = session.get(UserPreference, key)
            if pref is None:
                return default
            return pref.value

    def get_all_preferences(self) -> dict[str, str]:
        """Return all stored preferences as a plain dict."""
        with self._session() as session:
            rows = session.query(UserPreference).all()
            return {r.key: r.value for r in rows}

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def add_note(self, title: str, content: str = "", tags: str = "") -> Note:
        """Create a new note.

        Args:
            title: Note title.
            content: Body text.
            tags: Comma-separated tag string.

        Returns:
            The persisted :class:`~database.models.Note`.
        """
        with self._lock, self._session() as session:
            note = Note(title=title, content=content, tags=tags)
            session.add(note)
            session.commit()
            return note

    def get_notes(self, search: Optional[str] = None) -> List[dict]:
        """Return notes, optionally filtered by *search* text.

        Args:
            search: Optional string to match against title, content, or tags.

        Returns:
            List of note dicts ordered by creation date descending.
        """
        with self._session() as session:
            query = session.query(Note)
            if search:
                pattern = f"%{search}%"
                query = query.filter(
                    or_(
                        Note.title.ilike(pattern),
                        Note.content.ilike(pattern),
                        Note.tags.ilike(pattern),
                    )
                )
            rows = query.order_by(Note.created_at.desc()).all()
            return [r.to_dict() for r in rows]

    def update_note(
        self,
        note_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> bool:
        """Update fields of an existing note.

        Returns:
            ``True`` if the note was found and updated, ``False`` otherwise.
        """
        with self._lock, self._session() as session:
            note = session.get(Note, note_id)
            if note is None:
                return False
            if title is not None:
                note.title = title
            if content is not None:
                note.content = content
            if tags is not None:
                note.tags = tags
            note.updated_at = datetime.utcnow()
            session.commit()
            return True

    def delete_note(self, note_id: int) -> bool:
        """Delete a note by ID. Returns ``True`` if deleted."""
        with self._lock, self._session() as session:
            note = session.get(Note, note_id)
            if note is None:
                return False
            session.delete(note)
            session.commit()
            return True

    # ------------------------------------------------------------------
    # Reminders
    # ------------------------------------------------------------------

    def add_reminder(
        self,
        title: str,
        message: str,
        remind_at: datetime,
    ) -> Reminder:
        """Create a new reminder.

        Args:
            title: Short title for the reminder.
            message: Detailed reminder message.
            remind_at: UTC datetime when the reminder should fire.

        Returns:
            The persisted :class:`~database.models.Reminder`.
        """
        with self._lock, self._session() as session:
            reminder = Reminder(title=title, message=message, remind_at=remind_at)
            session.add(reminder)
            session.commit()
            return reminder

    def get_pending_reminders(self) -> List[dict]:
        """Return all incomplete reminders whose trigger time has passed."""
        now = datetime.utcnow()
        with self._session() as session:
            rows = (
                session.query(Reminder)
                .filter(Reminder.completed == False, Reminder.remind_at <= now)  # noqa: E712
                .order_by(Reminder.remind_at.asc())
                .all()
            )
            return [r.to_dict() for r in rows]

    def get_all_reminders(self, include_completed: bool = False) -> List[dict]:
        """Return reminders, optionally including completed ones."""
        with self._session() as session:
            query = session.query(Reminder)
            if not include_completed:
                query = query.filter(Reminder.completed == False)  # noqa: E712
            rows = query.order_by(Reminder.remind_at.asc()).all()
            return [r.to_dict() for r in rows]

    def complete_reminder(self, reminder_id: int) -> bool:
        """Mark a reminder as completed. Returns ``True`` if found."""
        with self._lock, self._session() as session:
            reminder = session.get(Reminder, reminder_id)
            if reminder is None:
                return False
            reminder.completed = True
            session.commit()
            return True

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def upsert_task(
        self,
        name: str,
        schedule: str = "",
        next_run: Optional[datetime] = None,
        active: bool = True,
    ) -> Task:
        """Create or update a scheduled task record.

        Args:
            name: Unique task name.
            schedule: Human-readable schedule description (e.g. ``"every 5m"``).
            next_run: Expected next execution time.
            active: Whether the task is currently active.

        Returns:
            The persisted :class:`~database.models.Task`.
        """
        with self._lock, self._session() as session:
            task = session.query(Task).filter_by(name=name).first()
            if task is None:
                task = Task(name=name, schedule=schedule, next_run=next_run, active=active)
                session.add(task)
            else:
                task.schedule = schedule
                task.next_run = next_run
                task.active = active
            session.commit()
            return task

    def record_task_run(self, name: str) -> bool:
        """Update *last_run* timestamp for the named task."""
        with self._lock, self._session() as session:
            task = session.query(Task).filter_by(name=name).first()
            if task is None:
                return False
            task.last_run = datetime.utcnow()
            session.commit()
            return True

    def get_active_tasks(self) -> List[dict]:
        """Return all active task records."""
        with self._session() as session:
            rows = session.query(Task).filter_by(active=True).all()
            return [r.to_dict() for r in rows]

    # ------------------------------------------------------------------
    # Activity log
    # ------------------------------------------------------------------

    def log_activity(
        self,
        action: str,
        details: str = "",
        user: str = "system",
    ) -> ActivityLog:
        """Append an entry to the activity log.

        Args:
            action: Short action identifier (e.g. ``"voice_command"``).
            details: Free-form details string.
            user: Actor performing the action.

        Returns:
            The persisted :class:`~database.models.ActivityLog`.
        """
        with self._lock, self._session() as session:
            entry = ActivityLog(action=action, details=details, user=user)
            session.add(entry)
            session.commit()
            return entry

    def get_activity_log(
        self,
        limit: int = 100,
        action_filter: Optional[str] = None,
    ) -> List[dict]:
        """Return recent activity log entries.

        Args:
            limit: Maximum number of entries to return.
            action_filter: If provided, only return entries with this action.
        """
        with self._session() as session:
            query = session.query(ActivityLog)
            if action_filter:
                query = query.filter(ActivityLog.action == action_filter)
            rows = (
                query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
            )
            return [r.to_dict() for r in rows]

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Dispose of the database connection pool."""
        self._engine.dispose()


# Module-level singleton factory
_manager_instance: DatabaseManager | None = None
_manager_lock = threading.Lock()


def get_db_manager(db_path: str = _DEFAULT_DB_PATH) -> DatabaseManager:
    """Return the module-level singleton :class:`DatabaseManager`.

    Args:
        db_path: Path to the SQLite file (used only on first call).
    """
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = DatabaseManager(db_path)
    return _manager_instance
