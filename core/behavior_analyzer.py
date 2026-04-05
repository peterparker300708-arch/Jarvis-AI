"""
Behavior Analyzer - Tracks user patterns and habits for Jarvis AI.
"""

import logging
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class BehaviorAnalyzer:
    """
    Analyzes user behavior patterns to:
    - Identify routine tasks
    - Suggest proactive actions
    - Detect anomalies in usage
    - Build behavioral profiles
    """

    def __init__(self, config: Config, db=None):
        self.config = config
        self.db = db
        self._command_history: List[Dict] = []
        self._hourly_commands: defaultdict = defaultdict(list)
        self._daily_patterns: defaultdict = defaultdict(Counter)
        self._category_frequency: Counter = Counter()
        self._session_start = datetime.now()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_command(self, command: str, category: str, success: bool = True):
        """Record a user command for behavioral analysis."""
        entry = {
            "command": command,
            "category": category,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "hour": datetime.now().hour,
            "weekday": datetime.now().weekday(),
        }
        self._command_history.append(entry)
        self._hourly_commands[datetime.now().hour].append(category)
        self._daily_patterns[datetime.now().weekday()][category] += 1
        self._category_frequency[category] += 1

        # Persist to DB if available
        if self.db:
            try:
                self.db.log_command(command, category, success)
            except Exception:
                pass

        # Keep history bounded to last 1000 entries
        if len(self._command_history) > 1000:
            self._command_history = self._command_history[-1000:]

    # ------------------------------------------------------------------
    # Pattern Analysis
    # ------------------------------------------------------------------

    def get_top_categories(self, n: int = 5) -> List[Dict]:
        """Return the top N most-used command categories."""
        return [{"category": cat, "count": cnt} for cat, cnt in self._category_frequency.most_common(n)]

    def get_peak_hours(self) -> List[int]:
        """Return hours with the most activity (top 3)."""
        hourly_counts = {h: len(cmds) for h, cmds in self._hourly_commands.items()}
        return sorted(hourly_counts, key=hourly_counts.get, reverse=True)[:3]  # type: ignore[arg-type]

    def get_routine_suggestions(self) -> List[str]:
        """Suggest recurring tasks based on observed patterns."""
        suggestions = []
        current_hour = datetime.now().hour
        current_weekday = datetime.now().weekday()

        # Check what category is most common at this hour
        if current_hour in self._hourly_commands:
            common = Counter(self._hourly_commands[current_hour]).most_common(1)
            if common:
                suggestions.append(f"You often do '{common[0][0]}' tasks at this time.")

        # Check what's most common on this weekday
        if current_weekday in self._daily_patterns:
            top = self._daily_patterns[current_weekday].most_common(1)
            if top:
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                suggestions.append(f"On {days[current_weekday]}s you frequently run '{top[0][0]}' tasks.")

        return suggestions

    def get_behavioral_profile(self) -> Dict:
        """Return a comprehensive behavioral profile."""
        total = len(self._command_history)
        success_count = sum(1 for c in self._command_history if c.get("success"))

        return {
            "total_commands": total,
            "success_rate": round(success_count / total, 3) if total else 0,
            "top_categories": self.get_top_categories(),
            "peak_hours": self.get_peak_hours(),
            "session_duration_minutes": round(
                (datetime.now() - self._session_start).total_seconds() / 60, 1
            ),
            "routine_suggestions": self.get_routine_suggestions(),
        }

    def detect_anomaly(self, command: str, category: str) -> bool:
        """
        Return True if this command/category is unusually rare
        (potential anomaly or new behavior).
        """
        if not self._category_frequency:
            return False
        freq = self._category_frequency.get(category, 0)
        total = sum(self._category_frequency.values())
        rate = freq / total if total else 0
        # Flag categories with less than 2% historical frequency
        return rate < 0.02

    def get_recent_history(self, n: int = 20) -> List[Dict]:
        """Return the N most recent commands."""
        return list(reversed(self._command_history[-n:]))

    def export_profile(self) -> str:
        """Export the behavioral profile as JSON."""
        return json.dumps(self.get_behavioral_profile(), indent=2)
