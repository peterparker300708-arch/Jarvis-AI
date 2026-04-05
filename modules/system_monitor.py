"""Real-time system monitor using psutil with thread-safe background monitoring."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)


class SystemMonitor:
    """Thread-safe real-time system resource monitor.

    Uses psutil to collect CPU, memory, disk, network, and process data.
    Supports background monitoring with a user-supplied callback.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_snapshot: Optional[Dict[str, Any]] = None

        if not _PSUTIL_AVAILABLE:
            logger.warning("psutil is not installed; system monitoring will be limited.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a point-in-time snapshot of key system metrics.

        Returns:
            dict with keys: cpu_percent, cpu_count, memory_total,
            memory_used, memory_percent, disk_total, disk_used,
            disk_percent, network_bytes_sent, network_bytes_recv,
            boot_time, uptime_str.
        """
        if not _PSUTIL_AVAILABLE:
            return self._unavailable_snapshot()

        with self._lock:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_count = psutil.cpu_count(logical=True)

                mem = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                net = psutil.net_io_counters()
                boot_ts = psutil.boot_time()
                boot_dt = datetime.fromtimestamp(boot_ts)
                uptime = datetime.now() - boot_dt
                uptime_str = self._format_uptime(uptime)

                snapshot = {
                    "cpu_percent": cpu_percent,
                    "cpu_count": cpu_count,
                    "memory_total": mem.total,
                    "memory_used": mem.used,
                    "memory_percent": mem.percent,
                    "disk_total": disk.total,
                    "disk_used": disk.used,
                    "disk_percent": disk.percent,
                    "network_bytes_sent": net.bytes_sent,
                    "network_bytes_recv": net.bytes_recv,
                    "boot_time": boot_dt.isoformat(),
                    "uptime_str": uptime_str,
                    "timestamp": datetime.now().isoformat(),
                }
                self._last_snapshot = snapshot
                return snapshot
            except Exception as exc:
                logger.error("Error collecting system snapshot: %s", exc)
                return self._unavailable_snapshot()

    def get_processes(self, sort_by: str = "cpu", limit: int = 20) -> List[Dict[str, Any]]:
        """Return a list of the top *limit* running processes.

        Args:
            sort_by: Field to sort by — "cpu", "memory", or "name".
            limit: Maximum number of processes to return.

        Returns:
            List of dicts with keys: pid, name, cpu_percent,
            memory_percent, memory_mb, status, username.
        """
        if not _PSUTIL_AVAILABLE:
            return []

        processes: List[Dict[str, Any]] = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "memory_info", "status", "username"]
        ):
            try:
                info = proc.info
                mem_mb = round(info["memory_info"].rss / (1024 * 1024), 2) if info.get("memory_info") else 0.0
                processes.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"] or "",
                        "cpu_percent": info["cpu_percent"] or 0.0,
                        "memory_percent": round(info["memory_percent"] or 0.0, 2),
                        "memory_mb": mem_mb,
                        "status": info["status"] or "",
                        "username": info["username"] or "",
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        sort_key = {
            "cpu": lambda p: p["cpu_percent"],
            "memory": lambda p: p["memory_percent"],
            "name": lambda p: p["name"].lower(),
        }.get(sort_by, lambda p: p["cpu_percent"])

        processes.sort(key=sort_key, reverse=(sort_by != "name"))
        return processes[:limit]

    def get_temperatures(self) -> Dict[str, Any]:
        """Return CPU/GPU temperature readings if available.

        Returns:
            dict mapping sensor labels to temperature values in Celsius,
            or an empty dict if temperatures are unavailable.
        """
        if not _PSUTIL_AVAILABLE:
            return {}

        result: Dict[str, Any] = {}
        if not hasattr(psutil, "sensors_temperatures"):
            return result

        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return result
            for chip_name, entries in temps.items():
                for entry in entries:
                    label = entry.label or chip_name
                    result[label] = {
                        "current": entry.current,
                        "high": entry.high,
                        "critical": entry.critical,
                        "chip": chip_name,
                    }
        except Exception as exc:
            logger.debug("Temperature reading not available: %s", exc)

        return result

    def monitor_loop(self, callback: Callable[[Dict[str, Any]], None], interval: float = 5.0) -> None:
        """Blocking loop that calls *callback* with a new snapshot every *interval* seconds.

        Intended to be run in a dedicated thread. Exits when :meth:`stop_monitoring`
        is called.

        Args:
            callback: Function receiving a snapshot dict on each tick.
            interval: Seconds between snapshots.
        """
        logger.info("Monitor loop started (interval=%.1fs)", interval)
        while not self._stop_event.is_set():
            try:
                snapshot = self.get_snapshot()
                callback(snapshot)
            except Exception as exc:
                logger.error("Error in monitor callback: %s", exc)
            self._stop_event.wait(timeout=interval)
        logger.info("Monitor loop stopped.")

    def start_monitoring(self, interval: float = 5.0, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        """Start background monitoring in a daemon thread.

        Args:
            interval: Seconds between snapshots.
            callback: Optional function called with each snapshot.
                      If omitted, snapshots are stored in :attr:`last_snapshot`.
        """
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Monitoring is already running.")
            return

        self._stop_event.clear()
        _callback = callback or self._default_callback
        self._monitor_thread = threading.Thread(
            target=self.monitor_loop,
            args=(_callback, interval),
            daemon=True,
            name="SystemMonitorThread",
        )
        self._monitor_thread.start()
        logger.info("Background system monitoring started.")

    def stop_monitoring(self) -> None:
        """Signal the background monitor thread to stop and join it."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        logger.info("Background system monitoring stopped.")

    @property
    def last_snapshot(self) -> Optional[Dict[str, Any]]:
        """Most recent snapshot produced by the background monitor."""
        return self._last_snapshot

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _default_callback(self, snapshot: Dict[str, Any]) -> None:
        self._last_snapshot = snapshot

    @staticmethod
    def _format_uptime(delta: timedelta) -> str:
        total_seconds = int(delta.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)

    @staticmethod
    def _unavailable_snapshot() -> Dict[str, Any]:
        return {
            "cpu_percent": 0.0,
            "cpu_count": 0,
            "memory_total": 0,
            "memory_used": 0,
            "memory_percent": 0.0,
            "disk_total": 0,
            "disk_used": 0,
            "disk_percent": 0.0,
            "network_bytes_sent": 0,
            "network_bytes_recv": 0,
            "boot_time": None,
            "uptime_str": "unavailable",
            "timestamp": datetime.now().isoformat(),
            "error": "psutil not available",
        }
