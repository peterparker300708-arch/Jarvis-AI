"""
Database Manager - SQLAlchemy database operations for Jarvis AI.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from database.models import (
    Base,
    AnalyticsEvent,
    CommandLog,
    MemoryEntry,
    Note,
    ScheduledTask,
    UserPreference,
    WikiArticle,
)
from utils.config import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages all database operations for Jarvis AI."""

    def __init__(self, config: Config):
        self.config = config
        db_path = config.get("database.path", "database/jarvis.db")
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self._engine)
        self._initialized = True
        logger.info("Database initialized")

    def session(self) -> Session:
        """Return a new SQLAlchemy session."""
        return Session(self._engine)

    # ------------------------------------------------------------------
    # Command Logging
    # ------------------------------------------------------------------

    def log_command(self, command: str, category: str = "general", success: bool = True,
                    response: str = "", duration_ms: float = 0) -> int:
        with self.session() as sess:
            entry = CommandLog(
                command=command,
                category=category,
                response=response,
                success=success,
                duration_ms=duration_ms,
            )
            sess.add(entry)
            sess.commit()
            return entry.id

    def get_command_history(self, limit: int = 50) -> List[Dict]:
        with self.session() as sess:
            rows = (
                sess.query(CommandLog)
                .order_by(CommandLog.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "command": r.command,
                    "category": r.category,
                    "success": r.success,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def save_memory_entry(self, entry: Dict) -> int:
        with self.session() as sess:
            mem = MemoryEntry(
                session_id=entry.get("session_id", ""),
                role=entry.get("role", "user"),
                content=entry.get("content", ""),
                metadata_json=json.dumps(entry.get("metadata", {})),
            )
            sess.add(mem)
            sess.commit()
            return mem.id

    def search_memory(self, query: str, limit: int = 5) -> List[Dict]:
        with self.session() as sess:
            rows = (
                sess.query(MemoryEntry)
                .filter(MemoryEntry.content.contains(query))
                .order_by(MemoryEntry.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "role": r.role,
                    "content": r.content,
                    "timestamp": r.created_at.isoformat() if r.created_at else None,
                    "session_id": r.session_id,
                }
                for r in rows
            ]

    def get_memory_sessions(self, limit: int = 20) -> List[Dict]:
        with self.session() as sess:
            result = sess.execute(
                text(
                    "SELECT session_id, MIN(created_at) as started, COUNT(*) as turns "
                    "FROM memory_entries GROUP BY session_id ORDER BY started DESC LIMIT :limit"
                ),
                {"limit": limit},
            )
            return [{"session_id": r[0], "started": str(r[1]), "turns": r[2]} for r in result]

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def save_note(self, title: str, content: str, tags: str = "", category: str = "general") -> int:
        with self.session() as sess:
            note = Note(title=title, content=content, tags=tags, category=category)
            sess.add(note)
            sess.commit()
            return note.id

    def get_notes(self, limit: int = 20) -> List[Dict]:
        with self.session() as sess:
            rows = sess.query(Note).order_by(Note.updated_at.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "content": r.content,
                    "tags": r.tags,
                    "category": r.category,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def log_event(self, event_type: str, data_json: str = "{}"):
        with self.session() as sess:
            event = AnalyticsEvent(event_type=event_type, data_json=data_json)
            sess.add(event)
            sess.commit()

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    def set_preference(self, key: str, value: str):
        with self.session() as sess:
            existing = sess.query(UserPreference).filter_by(key=key).first()
            if existing:
                existing.value = value
                existing.updated_at = datetime.now()
            else:
                sess.add(UserPreference(key=key, value=value))
            sess.commit()

    def get_preference(self, key: str, default: str = "") -> str:
        with self.session() as sess:
            pref = sess.query(UserPreference).filter_by(key=key).first()
            return pref.value if pref else default

    def get_all_preferences(self) -> Dict:
        with self.session() as sess:
            rows = sess.query(UserPreference).all()
            return {r.key: r.value for r in rows}

    # ------------------------------------------------------------------
    # Scheduled Tasks
    # ------------------------------------------------------------------

    def create_task(self, title: str, scheduled_time: datetime,
                    priority: str = "medium", description: str = "") -> int:
        with self.session() as sess:
            task = ScheduledTask(
                title=title,
                description=description,
                scheduled_time=scheduled_time,
                priority=priority,
            )
            sess.add(task)
            sess.commit()
            return task.id

    def get_pending_tasks(self) -> List[Dict]:
        with self.session() as sess:
            rows = (
                sess.query(ScheduledTask)
                .filter_by(status="pending")
                .order_by(ScheduledTask.scheduled_time)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "scheduled_time": r.scheduled_time.isoformat() if r.scheduled_time else None,
                    "priority": r.priority,
                    "status": r.status,
                }
                for r in rows
            ]

    def complete_task(self, task_id: int) -> bool:
        with self.session() as sess:
            task = sess.query(ScheduledTask).filter_by(id=task_id).first()
            if task:
                task.status = "completed"
                task.completed_at = datetime.now()
                sess.commit()
                return True
            return False
