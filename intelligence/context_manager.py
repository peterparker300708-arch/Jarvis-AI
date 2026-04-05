"""
Context Manager - Maintains situational awareness for Jarvis AI.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Tracks and provides contextual information:
    - Time of day / day of week
    - Current location (if available)
    - Active tasks
    - User availability
    - Device state
    """

    def __init__(self, config: Config, memory=None):
        self.config = config
        self.memory = memory
        self._context: Dict = {}
        self._active_task: Optional[str] = None
        self._focus_mode = False
        self._update_time_context()

    # ------------------------------------------------------------------

    def update(self, key: str, value):
        """Update a context value."""
        self._context[key] = value
        logger.debug(f"Context updated: {key}={value}")

    def get(self, key: str, default=None):
        """Get a context value."""
        return self._context.get(key, default)

    def get_full_context(self) -> Dict:
        """Return full current context."""
        self._update_time_context()
        return dict(self._context)

    def _update_time_context(self):
        now = datetime.now()
        hour = now.hour
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"

        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self._context.update(
            {
                "timestamp": now.isoformat(),
                "time_of_day": time_of_day,
                "hour": hour,
                "weekday": weekday_names[now.weekday()],
                "is_weekend": now.weekday() >= 5,
                "date": now.strftime("%Y-%m-%d"),
            }
        )

    # ------------------------------------------------------------------
    # Active Task Tracking
    # ------------------------------------------------------------------

    def set_active_task(self, task: str):
        self._active_task = task
        self._context["active_task"] = task

    def clear_active_task(self):
        self._active_task = None
        self._context.pop("active_task", None)

    def get_active_task(self) -> Optional[str]:
        return self._active_task

    # ------------------------------------------------------------------
    # Focus Mode
    # ------------------------------------------------------------------

    def enable_focus_mode(self):
        """Enable focus mode — suppress non-critical notifications."""
        self._focus_mode = True
        self._context["focus_mode"] = True
        logger.info("Focus mode enabled")

    def disable_focus_mode(self):
        self._focus_mode = False
        self._context["focus_mode"] = False
        logger.info("Focus mode disabled")

    def is_focus_mode(self) -> bool:
        return self._focus_mode

    # ------------------------------------------------------------------
    # Context Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> str:
        ctx = self.get_full_context()
        parts = [
            f"Time: {ctx.get('time_of_day', 'unknown')} ({ctx.get('date', '')})",
            f"Day: {ctx.get('weekday', 'unknown')}",
        ]
        if self._active_task:
            parts.append(f"Active task: {self._active_task}")
        if self._focus_mode:
            parts.append("Focus mode: ON")
        return " | ".join(parts)
