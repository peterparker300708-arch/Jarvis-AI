"""
Analytics Engine - Central analytics and reporting for Jarvis AI.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Aggregates and analyzes data from all Jarvis subsystems:
    - Command usage statistics
    - System performance history
    - User behavior trends
    - Custom metrics
    """

    def __init__(self, config: Config, db=None):
        self.config = config
        self.db = db
        self.retention_days = config.get("analytics.retention_days", 90)
        self.reports_dir = config.get("analytics.reports_dir", "reports")
        os.makedirs(self.reports_dir, exist_ok=True)
        self._metrics: List[Dict] = []
        self._events: List[Dict] = []

    # ------------------------------------------------------------------
    # Event Tracking
    # ------------------------------------------------------------------

    def track_event(self, event_type: str, data: Dict):
        """Record an analytics event."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        self._events.append(event)
        # Keep bounded
        if len(self._events) > 10000:
            self._events = self._events[-10000:]

        if self.db:
            try:
                self.db.log_event(event_type, json.dumps(data))
            except Exception:
                pass

    def track_metric(self, name: str, value: float, tags: Optional[Dict] = None):
        """Record a numeric metric data point."""
        self._metrics.append(
            {
                "name": name,
                "value": value,
                "tags": tags or {},
                "timestamp": datetime.now().isoformat(),
            }
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Dict]:
        """Return recent events of a given type."""
        filtered = [e for e in self._events if e["type"] == event_type]
        return list(reversed(filtered[-limit:]))

    def get_metrics(self, name: str, hours: int = 24) -> List[Dict]:
        """Return metric data points for the last N hours."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        return [m for m in self._metrics if m["name"] == name and m["timestamp"] >= cutoff]

    def get_daily_summary(self, date: Optional[str] = None) -> Dict:
        """Return a summary of activity for a given date (defaults to today)."""
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        day_events = [e for e in self._events if e.get("date") == target_date]

        event_counts: Dict[str, int] = {}
        for event in day_events:
            event_counts[event["type"]] = event_counts.get(event["type"], 0) + 1

        return {
            "date": target_date,
            "total_events": len(day_events),
            "event_breakdown": event_counts,
            "generated_at": datetime.now().isoformat(),
        }

    def get_trend(self, event_type: str, days: int = 7) -> List[Dict]:
        """Return daily counts for an event type over the last N days."""
        trend = []
        for i in range(days - 1, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            count = sum(1 for e in self._events if e.get("date") == date and e["type"] == event_type)
            trend.append({"date": date, "count": count})
        return trend

    def get_top_events(self, limit: int = 10) -> List[Dict]:
        """Return the most frequent event types."""
        from collections import Counter
        counts = Counter(e["type"] for e in self._events)
        return [{"event_type": et, "count": cnt} for et, cnt in counts.most_common(limit)]

    # ------------------------------------------------------------------
    # Report Generation
    # ------------------------------------------------------------------

    def generate_report(self, report_type: str = "daily") -> Dict:
        """Generate an analytics report."""
        if report_type == "daily":
            return self._daily_report()
        elif report_type == "weekly":
            return self._weekly_report()
        else:
            return self._daily_report()

    def _daily_report(self) -> Dict:
        summary = self.get_daily_summary()
        top_events = self.get_top_events(5)
        report = {
            "report_type": "daily",
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "top_events": top_events,
            "total_metrics": len(self._metrics),
        }
        self._save_report(report, "daily")
        return report

    def _weekly_report(self) -> Dict:
        daily_summaries = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_summaries.append(self.get_daily_summary(date))
        total_events = sum(s["total_events"] for s in daily_summaries)
        report = {
            "report_type": "weekly",
            "generated_at": datetime.now().isoformat(),
            "daily_breakdown": daily_summaries,
            "total_events_this_week": total_events,
        }
        self._save_report(report, "weekly")
        return report

    def _save_report(self, report: Dict, report_type: str):
        """Save report to disk."""
        filename = f"{report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.reports_dir, filename)
        try:
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
