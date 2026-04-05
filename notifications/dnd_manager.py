"""
Do Not Disturb Manager - Smart DND mode for Jarvis AI.
"""

import logging
from datetime import datetime, time as dtime
from typing import Dict, List, Optional, Tuple

from utils.config import Config

logger = logging.getLogger(__name__)


class DNDManager:
    """
    Manage Do Not Disturb mode:
    - Manual enable/disable
    - Scheduled DND windows
    - Exception rules (VIP senders, critical alerts)
    - Context-aware DND (detect focus hours)
    """

    def __init__(self, config: Config):
        self.config = config
        self._active = False
        self._schedules: List[Dict] = []
        self._exceptions: List[str] = ["critical"]  # Always allow critical priority

    # ------------------------------------------------------------------

    def enable(self, reason: str = "manual"):
        self._active = True
        logger.info(f"DND enabled ({reason})")

    def disable(self):
        self._active = False
        logger.info("DND disabled")

    def is_active(self) -> bool:
        """Return True if DND is currently active (manual or scheduled)."""
        if self._active:
            return True
        return self._in_scheduled_window()

    def should_suppress(self, priority: str = "normal") -> bool:
        """Return True if this notification should be suppressed."""
        if priority in self._exceptions:
            return False
        return self.is_active()

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def add_schedule(
        self,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int,
        days: Optional[List[int]] = None,
        name: str = "",
    ):
        """
        Schedule a DND window.
        days: list of weekday indices (0=Monday, 6=Sunday), None = every day
        """
        self._schedules.append(
            {
                "name": name or f"{start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d}",
                "start": (start_hour, start_minute),
                "end": (end_hour, end_minute),
                "days": days,
            }
        )

    def remove_schedule(self, name: str) -> bool:
        before = len(self._schedules)
        self._schedules = [s for s in self._schedules if s["name"] != name]
        return len(self._schedules) < before

    def _in_scheduled_window(self) -> bool:
        now = datetime.now()
        current_time = (now.hour, now.minute)
        current_day = now.weekday()
        for schedule in self._schedules:
            if schedule["days"] and current_day not in schedule["days"]:
                continue
            if schedule["start"] <= current_time < schedule["end"]:
                return True
        return False

    def get_schedules(self) -> List[Dict]:
        return list(self._schedules)

    # ------------------------------------------------------------------
    # Exceptions
    # ------------------------------------------------------------------

    def add_exception(self, priority: str):
        if priority not in self._exceptions:
            self._exceptions.append(priority)

    def remove_exception(self, priority: str):
        if priority in self._exceptions:
            self._exceptions.remove(priority)

    def get_status(self) -> Dict:
        return {
            "active": self.is_active(),
            "manual_override": self._active,
            "in_schedule": self._in_scheduled_window(),
            "exceptions": self._exceptions,
            "scheduled_windows": len(self._schedules),
        }
