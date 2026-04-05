"""
Recommendation Engine - Suggest tasks based on user history and patterns.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Suggests tasks, commands, and actions based on:
    - Historical usage patterns
    - Time of day / day of week
    - Current context
    - ML predictions
    """

    # Time-based default suggestions
    TIME_SUGGESTIONS = {
        "morning": [
            "Check your emails",
            "Review today's calendar",
            "Get the morning news briefing",
            "Check system health status",
        ],
        "afternoon": [
            "Review pending tasks",
            "Check project progress",
            "Analyze performance metrics",
            "Prepare afternoon report",
        ],
        "evening": [
            "Summarize today's activities",
            "Schedule tomorrow's tasks",
            "Backup important files",
            "Review daily analytics",
        ],
        "night": [
            "Set reminders for tomorrow",
            "Run system cleanup",
            "Check scheduled tasks",
            "Review notifications",
        ],
    }

    def __init__(self, config: Config, db=None, behavior_analyzer=None):
        self.config = config
        self.db = db
        self.behavior_analyzer = behavior_analyzer
        self._accepted: List[str] = []
        self._rejected: List[str] = []

    # ------------------------------------------------------------------
    # Core Recommendation
    # ------------------------------------------------------------------

    def get_recommendations(self, context: Optional[Dict] = None, n: int = 5) -> List[Dict]:
        """Generate ranked recommendations for the user."""
        recommendations = []

        # Time-based suggestions
        time_recs = self._time_based_suggestions()
        for rec in time_recs:
            recommendations.append(
                {
                    "text": rec,
                    "source": "time_based",
                    "priority": "medium",
                    "score": 0.6,
                }
            )

        # Behavior-based suggestions
        if self.behavior_analyzer:
            behavior_recs = self._behavior_based_suggestions()
            for rec in behavior_recs:
                recommendations.append(
                    {
                        "text": rec,
                        "source": "behavior",
                        "priority": "high",
                        "score": 0.8,
                    }
                )

        # Context-based
        if context:
            ctx_recs = self._context_based_suggestions(context)
            for rec in ctx_recs:
                recommendations.append(
                    {
                        "text": rec,
                        "source": "context",
                        "priority": "high",
                        "score": 0.85,
                    }
                )

        # Remove previously rejected suggestions
        recommendations = [r for r in recommendations if r["text"] not in self._rejected]

        # Sort by score descending
        recommendations.sort(key=lambda r: r["score"], reverse=True)
        return recommendations[:n]

    def _time_based_suggestions(self) -> List[str]:
        """Suggest tasks appropriate for the current time of day."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 17:
            period = "afternoon"
        elif 17 <= hour < 21:
            period = "evening"
        else:
            period = "night"
        return self.TIME_SUGGESTIONS.get(period, [])[:2]

    def _behavior_based_suggestions(self) -> List[str]:
        """Use behavioral patterns to suggest next actions."""
        if not self.behavior_analyzer:
            return []
        profile = self.behavior_analyzer.get_behavioral_profile()
        top_categories = profile.get("top_categories", [])
        suggestions = []
        for item in top_categories[:2]:
            cat = item["category"]
            suggestions.append(f"You often run {cat} tasks — want to continue?")
        suggestions.extend(profile.get("routine_suggestions", []))
        return suggestions[:3]

    def _context_based_suggestions(self, context: Dict) -> List[str]:
        """Generate context-aware suggestions."""
        suggestions = []
        if context.get("high_cpu"):
            suggestions.append("System CPU is high — want to check running processes?")
        if context.get("unread_emails"):
            suggestions.append(f"You have {context['unread_emails']} unread emails.")
        if context.get("pending_tasks"):
            suggestions.append(f"{context['pending_tasks']} tasks are pending.")
        return suggestions

    # ------------------------------------------------------------------
    # Feedback Loop
    # ------------------------------------------------------------------

    def accept_recommendation(self, text: str):
        """Mark a recommendation as accepted (positive feedback)."""
        self._accepted.append(text)
        if text in self._rejected:
            self._rejected.remove(text)

    def reject_recommendation(self, text: str):
        """Mark a recommendation as rejected (negative feedback)."""
        self._rejected.append(text)

    def get_acceptance_rate(self) -> float:
        """Return the acceptance rate of recommendations."""
        total = len(self._accepted) + len(self._rejected)
        return round(len(self._accepted) / total, 3) if total else 0.0
