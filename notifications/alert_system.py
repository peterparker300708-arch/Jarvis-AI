"""
Alert System - System health and event-based alerts.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class AlertSystem:
    """Monitors thresholds and fires alerts when they are breached."""

    DEFAULT_THRESHOLDS = {
        "cpu_percent": 90.0,
        "ram_percent": 90.0,
        "disk_percent": 90.0,
        "net_sent_kbps": 10000.0,
    }

    def __init__(self, config: Config, notification_engine=None):
        self.config = config
        self.notification_engine = notification_engine
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)
        self._alerts: List[Dict] = []
        self._suppressed: Dict[str, str] = {}  # metric -> last_alert_time

    # ------------------------------------------------------------------

    def set_threshold(self, metric: str, value: float):
        self.thresholds[metric] = value

    def check_metrics(self, metrics: Dict) -> List[Dict]:
        """Check a metrics dict against thresholds. Fire alerts for breaches."""
        triggered = []
        now = datetime.now().isoformat()
        for metric, threshold in self.thresholds.items():
            val = metrics.get(metric)
            if val is None:
                continue
            if val > threshold:
                # Deduplicate alerts within 5 minutes
                last = self._suppressed.get(metric)
                if last:
                    from datetime import datetime as dt
                    elapsed = (dt.now() - dt.fromisoformat(last)).total_seconds()
                    if elapsed < 300:
                        continue

                alert = {
                    "metric": metric,
                    "value": val,
                    "threshold": threshold,
                    "timestamp": now,
                    "severity": "critical" if val > threshold * 1.1 else "warning",
                }
                self._alerts.append(alert)
                self._suppressed[metric] = now
                triggered.append(alert)

                if self.notification_engine:
                    label = metric.replace("_", " ").title()
                    self.notification_engine.notify(
                        title=f"⚠️ {label} Alert",
                        message=f"{label} is at {val:.1f}% (threshold: {threshold}%)",
                        priority="high" if alert["severity"] == "warning" else "critical",
                    )
                else:
                    logger.warning(f"ALERT: {metric}={val} exceeds threshold {threshold}")

        return triggered

    def get_active_alerts(self) -> List[Dict]:
        """Return alerts from the last 10 minutes."""
        from datetime import datetime as dt, timedelta
        cutoff = (dt.now() - timedelta(minutes=10)).isoformat()
        return [a for a in self._alerts if a["timestamp"] >= cutoff]

    def get_all_alerts(self, limit: int = 100) -> List[Dict]:
        return list(reversed(self._alerts[-limit:]))

    def clear_alerts(self):
        self._alerts.clear()
        self._suppressed.clear()

    def get_alert_summary(self) -> Dict:
        recent = self.get_active_alerts()
        return {
            "active_count": len(recent),
            "total_count": len(self._alerts),
            "thresholds": self.thresholds,
        }
