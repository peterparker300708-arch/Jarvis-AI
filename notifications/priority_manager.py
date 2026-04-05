"""
Priority Manager - Manage notification priority and routing.
"""

import logging
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class PriorityManager:
    """
    Determines notification priority and routes to appropriate channels.
    """

    PRIORITY_LEVELS = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "normal": 1,
        "low": 0,
    }

    PRIORITY_CHANNELS = {
        "critical": ["desktop", "telegram", "email"],
        "high": ["desktop", "telegram"],
        "medium": ["desktop"],
        "normal": ["console"],
        "low": ["console"],
    }

    def __init__(self, config: Config):
        self.config = config
        self._rules: List[Dict] = []

    def add_rule(self, keyword: str, priority: str, channel: Optional[str] = None):
        """Add a priority rule based on keyword matching."""
        self._rules.append(
            {"keyword": keyword.lower(), "priority": priority, "channel": channel}
        )

    def assess_priority(self, title: str, message: str) -> Dict:
        """Determine the priority and channel for a notification."""
        combined = (title + " " + message).lower()

        # Check custom rules first
        for rule in self._rules:
            if rule["keyword"] in combined:
                priority = rule["priority"]
                channel = rule.get("channel") or self.PRIORITY_CHANNELS.get(priority, ["console"])[0]
                return {"priority": priority, "channel": channel, "rule_matched": rule["keyword"]}

        # Keyword-based heuristics
        if any(w in combined for w in ("critical", "emergency", "failure", "crash", "error")):
            priority = "critical"
        elif any(w in combined for w in ("warning", "alert", "high", "urgent", "important")):
            priority = "high"
        elif any(w in combined for w in ("reminder", "scheduled", "due")):
            priority = "medium"
        else:
            priority = "normal"

        channels = self.PRIORITY_CHANNELS.get(priority, ["console"])
        return {"priority": priority, "channel": channels[0], "rule_matched": None}

    def get_priority_score(self, priority: str) -> int:
        return self.PRIORITY_LEVELS.get(priority, 1)

    def filter_notifications(self, notifications: List[Dict], min_priority: str = "normal") -> List[Dict]:
        """Filter notifications by minimum priority level."""
        min_score = self.PRIORITY_LEVELS.get(min_priority, 1)
        return [n for n in notifications if self.PRIORITY_LEVELS.get(n.get("priority", "normal"), 1) >= min_score]
