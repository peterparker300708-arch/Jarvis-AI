"""
Digest Generator - Create email and daily digest summaries.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class DigestGenerator:
    """Generate daily / weekly digest summaries."""

    def __init__(self, config: Config, analytics_engine=None, notification_engine=None):
        self.config = config
        self.analytics_engine = analytics_engine
        self.notification_engine = notification_engine
        self._digests: List[Dict] = []

    # ------------------------------------------------------------------

    def generate_daily_digest(self) -> Dict:
        """Generate a daily digest report."""
        today = datetime.now().strftime("%Y-%m-%d")
        content: Dict = {
            "type": "daily",
            "date": today,
            "generated_at": datetime.now().isoformat(),
            "sections": {},
        }

        if self.analytics_engine:
            summary = self.analytics_engine.get_daily_summary(today)
            content["sections"]["activity"] = summary

        content["sections"]["system"] = {
            "message": "System has been running normally",
            "alerts": 0,
        }

        digest = {
            "id": len(self._digests) + 1,
            "type": "daily",
            "date": today,
            "content": content,
        }
        self._digests.append(digest)
        return digest

    def generate_weekly_digest(self) -> Dict:
        """Generate a weekly digest report."""
        week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        week_end = datetime.now().strftime("%Y-%m-%d")

        content: Dict = {
            "type": "weekly",
            "period": f"{week_start} to {week_end}",
            "generated_at": datetime.now().isoformat(),
            "sections": {},
        }

        if self.analytics_engine:
            content["sections"]["weekly_stats"] = self.analytics_engine.generate_report("weekly")

        digest = {
            "id": len(self._digests) + 1,
            "type": "weekly",
            "period": content["period"],
            "content": content,
        }
        self._digests.append(digest)
        return digest

    def send_digest(self, digest: Dict) -> bool:
        """Send the digest via configured notification channel."""
        if not self.notification_engine:
            return False
        title = f"Jarvis Digest - {digest.get('type', '').title()} ({digest.get('date', '')})"
        message = f"Your {digest.get('type', 'daily')} digest is ready. {len(digest.get('content', {}).get('sections', {}))} sections."
        return self.notification_engine.notify(
            title=title,
            message=message,
            priority="low",
            channel="email",
        )

    def get_digests(self, n: int = 10) -> List[Dict]:
        return list(reversed(self._digests[-n:]))
