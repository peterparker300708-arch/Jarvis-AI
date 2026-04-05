"""Calendar and reminder manager backed by the Jarvis SQLite database."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from database.db_manager import get_db_manager
from utils.logger import get_logger

logger = get_logger(__name__)

_CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS calendar_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    start_time  TEXT NOT NULL,
    end_time    TEXT,
    description TEXT DEFAULT '',
    location    TEXT DEFAULT '',
    created_at  TEXT NOT NULL
)
"""


def _get_events_db_path() -> str:
    """Resolve the SQLite path used by the existing db_manager."""
    import os
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "jarvis.db"
    )


class CalendarManager:
    """Manages calendar events and reminders using the Jarvis SQLite database.

    Events are stored in a ``calendar_events`` table.
    Reminders are stored in the existing ``reminders`` table via :class:`DatabaseManager`.
    """

    def __init__(self) -> None:
        self._db_manager = get_db_manager()
        self._db_path = _get_events_db_path()
        self._lock = threading.Lock()
        self._reminder_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._ensure_events_table()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def add_event(
        self,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        description: str = "",
        location: str = "",
    ) -> Dict[str, Any]:
        """Add a calendar event.

        Args:
            title: Event title.
            start_time: Event start as a datetime object.
            end_time: Optional event end datetime.
            description: Optional description text.
            location: Optional location string.

        Returns:
            dict representing the created event.
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO calendar_events
                        (title, start_time, end_time, description, location, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title,
                        start_time.isoformat(),
                        end_time.isoformat() if end_time else None,
                        description,
                        location,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
                event_id = cursor.lastrowid
                logger.info("Added calendar event #%d: %s", event_id, title)
                return {
                    "event_id": event_id,
                    "title": title,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat() if end_time else None,
                    "description": description,
                    "location": location,
                }
            finally:
                conn.close()

    def get_events(
        self,
        date: Optional[datetime] = None,
        days_ahead: int = 7,
    ) -> List[Dict[str, Any]]:
        """Retrieve upcoming calendar events.

        Args:
            date: Start date for the window. Defaults to now.
            days_ahead: Number of days to look ahead.

        Returns:
            List of event dicts sorted by start_time.
        """
        start = date or datetime.now(timezone.utc)
        end = start + timedelta(days=days_ahead)

        with self._lock:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM calendar_events
                    WHERE start_time >= ? AND start_time <= ?
                    ORDER BY start_time ASC
                    """,
                    (start.isoformat(), end.isoformat()),
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def delete_event(self, event_id: int) -> bool:
        """Delete an event by ID.

        Returns:
            True if the event was found and deleted.
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.execute(
                    "DELETE FROM calendar_events WHERE event_id = ?", (event_id,)
                )
                conn.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info("Deleted calendar event #%d", event_id)
                return deleted
            finally:
                conn.close()

    def format_events_for_voice(self, events: List[Dict[str, Any]]) -> str:
        """Format a list of events as a human-readable string suitable for TTS.

        Args:
            events: List of event dicts from :meth:`get_events`.

        Returns:
            Multi-line string describing the events.
        """
        if not events:
            return "You have no upcoming events."

        lines = [f"You have {len(events)} upcoming event(s):"]
        for ev in events:
            start = ev.get("start_time", "")
            try:
                dt = datetime.fromisoformat(start)
                time_str = dt.strftime("%A, %B %d at %I:%M %p")
            except (ValueError, TypeError):
                time_str = start
            line = f"  - {ev['title']} on {time_str}"
            if ev.get("location"):
                line += f" at {ev['location']}"
            lines.append(line)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Reminders (delegated to DatabaseManager)
    # ------------------------------------------------------------------

    def add_reminder(self, title: str, message: str, remind_at: datetime) -> Dict[str, Any]:
        """Add a reminder via the database manager.

        Args:
            title: Short reminder title.
            message: Detailed reminder message.
            remind_at: UTC datetime when the reminder should fire.

        Returns:
            The created reminder as a dict.
        """
        reminder = self._db_manager.add_reminder(title=title, message=message, remind_at=remind_at)
        return reminder.to_dict()

    def get_reminders(self, upcoming_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve reminders.

        Args:
            upcoming_only: If True, exclude completed reminders.

        Returns:
            List of reminder dicts ordered by remind_at ascending.
        """
        return self._db_manager.get_all_reminders(include_completed=not upcoming_only)

    def check_reminders(self) -> List[Dict[str, Any]]:
        """Check for due reminders and mark them as completed.

        Calls any registered callbacks with each due reminder.

        Returns:
            List of reminder dicts that were due.
        """
        due = self._db_manager.get_pending_reminders()
        for reminder in due:
            self._db_manager.complete_reminder(reminder["reminder_id"])
            logger.info("Reminder fired: %s", reminder["title"])
            for cb in self._reminder_callbacks:
                try:
                    cb(reminder)
                except Exception as exc:
                    logger.error("Reminder callback error: %s", exc)
        return due

    def register_reminder_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a function to be called when a reminder fires.

        Args:
            callback: Function receiving the reminder dict.
        """
        self._reminder_callbacks.append(callback)

    def format_reminders_for_voice(self, reminders: List[Dict[str, Any]]) -> str:
        """Format reminders as a TTS-friendly string.

        Returns:
            Multi-line string describing upcoming reminders.
        """
        if not reminders:
            return "You have no upcoming reminders."

        lines = [f"You have {len(reminders)} reminder(s):"]
        for r in reminders:
            remind_at = r.get("remind_at", "")
            try:
                dt = datetime.fromisoformat(remind_at)
                time_str = dt.strftime("%A, %B %d at %I:%M %p")
            except (ValueError, TypeError):
                time_str = remind_at
            lines.append(f"  - {r['title']}: {r.get('message', '')} on {time_str}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_events_table(self) -> None:
        """Create the calendar_events table if it does not already exist."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(_CREATE_EVENTS_TABLE)
            conn.commit()
        finally:
            conn.close()
