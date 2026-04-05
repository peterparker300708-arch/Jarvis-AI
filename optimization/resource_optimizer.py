"""
Resource Optimizer - CPU, RAM and disk optimization for Jarvis AI.
"""

import gc
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List

import psutil

from utils.config import Config

logger = logging.getLogger(__name__)


class ResourceOptimizer:
    """
    Optimize system resource usage:
    - Garbage collection
    - Temp file cleanup
    - Process priority management
    - Disk cleanup
    """

    def __init__(self, config: Config):
        self.config = config

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def free_memory(self) -> Dict:
        """Run garbage collection and return memory delta."""
        before = psutil.virtual_memory().used
        gc.collect()
        after = psutil.virtual_memory().used
        freed_mb = round((before - after) / 1e6, 2)
        logger.info(f"Memory freed: {freed_mb} MB")
        return {
            "freed_mb": max(freed_mb, 0),
            "current_percent": psutil.virtual_memory().percent,
        }

    # ------------------------------------------------------------------
    # Disk Cleanup
    # ------------------------------------------------------------------

    def cleanup_temp_files(self) -> Dict:
        """Remove files from the system temp directory."""
        temp_dir = tempfile.gettempdir()
        removed = 0
        freed_bytes = 0
        errors = []
        for item in Path(temp_dir).iterdir():
            try:
                if item.is_file():
                    size = item.stat().st_size
                    item.unlink()
                    removed += 1
                    freed_bytes += size
                elif item.is_dir():
                    size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    shutil.rmtree(str(item), ignore_errors=True)
                    removed += 1
                    freed_bytes += size
            except Exception as e:
                errors.append(str(e))

        result = {
            "files_removed": removed,
            "freed_mb": round(freed_bytes / 1e6, 2),
            "errors": len(errors),
        }
        logger.info(f"Temp cleanup: removed {removed} items, freed {result['freed_mb']} MB")
        return result

    def cleanup_old_logs(self, logs_dir: str = "logs", days: int = 7) -> int:
        """Delete log files older than `days` days."""
        if not os.path.exists(logs_dir):
            return 0
        cutoff = time.time() - days * 86400
        removed = 0
        for f in Path(logs_dir).glob("*.log*"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        logger.info(f"Cleaned {removed} old log files")
        return removed

    def get_large_files(self, directory: str, min_size_mb: float = 100) -> List[Dict]:
        """Find files larger than min_size_mb in a directory."""
        min_bytes = min_size_mb * 1e6
        results = []
        for f in Path(directory).rglob("*"):
            try:
                if f.is_file() and f.stat().st_size > min_bytes:
                    results.append(
                        {
                            "path": str(f),
                            "size_mb": round(f.stat().st_size / 1e6, 2),
                        }
                    )
            except Exception:
                pass
        return sorted(results, key=lambda x: -x["size_mb"])

    # ------------------------------------------------------------------
    # Process Priority
    # ------------------------------------------------------------------

    def set_process_priority(self, pid: int, priority: str = "normal") -> bool:
        """
        Set process priority.
        priority: 'low' | 'normal' | 'high'
        """
        PRIORITY_MAP = {
            "low": psutil.IDLE_PRIORITY_CLASS if os.name == "nt" else 19,
            "normal": psutil.NORMAL_PRIORITY_CLASS if os.name == "nt" else 0,
            "high": psutil.HIGH_PRIORITY_CLASS if os.name == "nt" else -10,
        }
        try:
            proc = psutil.Process(pid)
            nice_val = PRIORITY_MAP.get(priority, 0)
            if os.name == "nt":
                proc.nice(nice_val)
            else:
                proc.nice(int(nice_val))
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
            logger.warning(f"set_process_priority failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_optimization_report(self) -> Dict:
        """Return a current resource usage report."""
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "ram_used_gb": round(mem.used / 1e9, 2),
            "ram_total_gb": round(mem.total / 1e9, 2),
            "ram_percent": mem.percent,
            "disk_used_gb": round(disk.used / 1e9, 2),
            "disk_total_gb": round(disk.total / 1e9, 2),
            "disk_percent": disk.percent,
            "process_count": len(psutil.pids()),
        }
