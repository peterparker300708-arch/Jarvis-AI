"""
Performance Tracker - System performance monitoring for Jarvis AI.
"""

import logging
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

import psutil

from utils.config import Config

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Tracks system performance metrics over time:
    - CPU, RAM, Disk, Network usage
    - Historical data storage
    - Anomaly alerts
    - Performance scoring
    """

    def __init__(self, config: Config, max_history: int = 1000):
        self.config = config
        self._history: deque = deque(maxlen=max_history)
        self._last_net_io = psutil.net_io_counters()
        self._last_sample_time = time.time()

    # ------------------------------------------------------------------

    def sample(self) -> Dict:
        """Collect a performance snapshot."""
        now = time.time()
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Network bandwidth calculation
        net_io = psutil.net_io_counters()
        elapsed = now - self._last_sample_time
        bytes_sent_ps = (net_io.bytes_sent - self._last_net_io.bytes_sent) / max(elapsed, 1)
        bytes_recv_ps = (net_io.bytes_recv - self._last_net_io.bytes_recv) / max(elapsed, 1)
        self._last_net_io = net_io
        self._last_sample_time = now

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(mem.percent, 1),
            "ram_used_gb": round(mem.used / 1e9, 2),
            "disk_percent": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / 1e9, 2),
            "net_sent_kbps": round(bytes_sent_ps / 1024, 2),
            "net_recv_kbps": round(bytes_recv_ps / 1024, 2),
            "load_avg": self._get_load_avg(),
        }

        self._history.append(snapshot)
        return snapshot

    def _get_load_avg(self) -> Optional[List[float]]:
        """Get system load average (not available on Windows)."""
        try:
            load = psutil.getloadavg()
            return [round(l, 2) for l in load]
        except AttributeError:
            return None

    # ------------------------------------------------------------------
    # History & Statistics
    # ------------------------------------------------------------------

    def get_history(self, n: int = 60) -> List[Dict]:
        """Return the last N performance snapshots."""
        history_list = list(self._history)
        return history_list[-n:]

    def get_averages(self, n: int = 10) -> Dict:
        """Return average metrics over the last N samples."""
        recent = list(self._history)[-n:]
        if not recent:
            return {}
        keys = ["cpu_percent", "ram_percent", "disk_percent"]
        return {
            k: round(sum(s.get(k, 0) for s in recent) / len(recent), 2)
            for k in keys
        }

    def get_peaks(self, n: int = 100) -> Dict:
        """Return peak values in the last N samples."""
        recent = list(self._history)[-n:]
        if not recent:
            return {}
        keys = ["cpu_percent", "ram_percent", "disk_percent"]
        return {k: max((s.get(k, 0) for s in recent), default=0) for k in keys}

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def check_alerts(self, thresholds: Optional[Dict] = None) -> List[str]:
        """
        Check if any metric exceeds its threshold.
        Returns list of alert messages.
        """
        if not self._history:
            return []
        defaults = {"cpu_percent": 90, "ram_percent": 90, "disk_percent": 90}
        thresholds = thresholds or defaults
        latest = self._history[-1]
        alerts = []
        for metric, threshold in thresholds.items():
            val = latest.get(metric, 0)
            if val > threshold:
                alerts.append(f"⚠️ {metric.replace('_', ' ').title()} is at {val}% (threshold: {threshold}%)")
        return alerts

    # ------------------------------------------------------------------
    # Performance Score
    # ------------------------------------------------------------------

    def get_health_score(self) -> int:
        """
        Return a health score 0-100 based on current metrics.
        100 = perfect health.
        """
        if not self._history:
            return 100
        latest = self._history[-1]
        cpu = latest.get("cpu_percent", 0)
        ram = latest.get("ram_percent", 0)
        disk = latest.get("disk_percent", 0)
        score = 100 - (cpu * 0.4 + ram * 0.4 + disk * 0.2)
        return max(0, int(score))

    def get_process_stats(self, top_n: int = 10) -> List[Dict]:
        """Return top processes by memory usage."""
        procs = []
        for proc in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
            try:
                procs.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(procs, key=lambda p: p.get("memory_percent", 0), reverse=True)[:top_n]
