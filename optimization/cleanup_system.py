"""
Cleanup System - Auto-maintenance and storage optimization.
"""

import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from utils.config import Config

logger = logging.getLogger(__name__)


class CleanupSystem:
    """
    Automated cleanup tasks:
    - Remove duplicate files
    - Archive old files
    - Rotate logs
    - Clear caches
    - Report generation cleanup
    """

    def __init__(self, config: Config):
        self.config = config
        self._cleanup_history: List[Dict] = []

    # ------------------------------------------------------------------

    def run_full_cleanup(self) -> Dict:
        """Execute all cleanup tasks and return a summary."""
        results = {
            "started_at": datetime.now().isoformat(),
            "tasks": {},
        }

        # 1. Log rotation
        logs_cleaned = self._rotate_logs()
        results["tasks"]["log_rotation"] = logs_cleaned

        # 2. Report cleanup
        reports_cleaned = self._cleanup_reports()
        results["tasks"]["report_cleanup"] = reports_cleaned

        # 3. Model state save (if ml_models available)
        results["tasks"]["temp_cleanup"] = self._cleanup_temp_patterns()

        results["finished_at"] = datetime.now().isoformat()
        self._cleanup_history.append(results)
        return results

    def _rotate_logs(self, logs_dir: str = "logs", max_size_mb: float = 50, keep_days: int = 7) -> Dict:
        """Rotate and remove old log files."""
        if not os.path.exists(logs_dir):
            return {"removed": 0}
        cutoff = time.time() - keep_days * 86400
        removed = 0
        for f in Path(logs_dir).glob("*.log*"):
            try:
                stat = f.stat()
                if stat.st_mtime < cutoff or stat.st_size > max_size_mb * 1e6:
                    f.unlink()
                    removed += 1
            except Exception:
                pass
        return {"removed": removed}

    def _cleanup_reports(self, max_reports: int = 50) -> Dict:
        """Keep only the most recent N reports."""
        reports_dir = self.config.get("analytics.reports_dir", "reports")
        if not os.path.exists(reports_dir):
            return {"removed": 0}
        files = sorted(
            [f for f in Path(reports_dir).iterdir() if f.is_file()],
            key=lambda f: f.stat().st_mtime,
        )
        removed = 0
        while len(files) > max_reports:
            files[0].unlink()
            files.pop(0)
            removed += 1
        return {"removed": removed, "kept": len(files)}

    def _cleanup_temp_patterns(self, patterns: List[str] = None) -> Dict:
        """Remove temp files matching common patterns."""
        patterns = patterns or ["*.tmp", "*.temp", "__pycache__", "*.pyc"]
        removed = 0
        for pattern in patterns:
            for f in Path(".").rglob(pattern):
                try:
                    if f.is_file():
                        f.unlink()
                        removed += 1
                    elif f.is_dir():
                        shutil.rmtree(str(f), ignore_errors=True)
                        removed += 1
                except Exception:
                    pass
        return {"removed": removed}

    def find_duplicates(self, directory: str) -> List[Dict]:
        """Find duplicate files by size and hash."""
        import hashlib
        size_map: Dict[int, List[Path]] = {}
        for f in Path(directory).rglob("*"):
            if f.is_file():
                size = f.stat().st_size
                size_map.setdefault(size, []).append(f)

        duplicates = []
        for size, files in size_map.items():
            if len(files) > 1:
                hash_map: Dict[str, List[Path]] = {}
                for f in files:
                    try:
                        h = hashlib.md5(f.read_bytes()).hexdigest()
                        hash_map.setdefault(h, []).append(f)
                    except Exception:
                        pass
                for h, dups in hash_map.items():
                    if len(dups) > 1:
                        duplicates.append(
                            {
                                "hash": h,
                                "size_kb": round(size / 1024, 2),
                                "files": [str(d) for d in dups],
                            }
                        )
        return duplicates

    def archive_old_files(
        self,
        source_dir: str,
        archive_dir: str,
        days_old: int = 90,
    ) -> Dict:
        """Move files older than `days_old` to an archive directory."""
        cutoff = time.time() - days_old * 86400
        os.makedirs(archive_dir, exist_ok=True)
        moved = 0
        for f in Path(source_dir).iterdir():
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    dest = Path(archive_dir) / f.name
                    shutil.move(str(f), str(dest))
                    moved += 1
            except Exception:
                pass
        return {"moved": moved, "archive_dir": archive_dir}

    def get_history(self) -> List[Dict]:
        return list(reversed(self._cleanup_history))
