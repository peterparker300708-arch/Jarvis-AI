"""
Download Manager - Smart file downloads with auto-organization.
"""

import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

from utils.config import Config

logger = logging.getLogger(__name__)


class DownloadTask:
    def __init__(self, task_id: str, url: str, dest_path: str):
        self.task_id = task_id
        self.url = url
        self.dest_path = dest_path
        self.status = "pending"  # pending | downloading | completed | failed
        self.progress = 0
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.error: Optional[str] = None


class DownloadManager:
    """Smart download manager with auto-categorization."""

    CATEGORY_EXTENSIONS = {
        "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"},
        "Documents": {".pdf", ".doc", ".docx", ".txt", ".odt", ".ppt", ".pptx"},
        "Videos": {".mp4", ".avi", ".mkv", ".mov", ".wmv"},
        "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg"},
        "Archives": {".zip", ".tar", ".gz", ".rar", ".7z"},
        "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".yaml"},
        "Executables": {".exe", ".msi", ".deb", ".dmg", ".sh"},
    }

    def __init__(self, config: Config):
        self.config = config
        self.downloads_dir = Path(config.get("paths.downloads", "~/Downloads")).expanduser()
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: Dict[str, DownloadTask] = {}
        self._task_counter = 0

    # ------------------------------------------------------------------

    def download(
        self,
        url: str,
        filename: Optional[str] = None,
        category_folder: bool = True,
        on_progress: Optional[Callable[[float], None]] = None,
        async_download: bool = False,
    ) -> Optional[str]:
        """Download a file from a URL."""
        task = self._create_task(url, filename, category_folder)
        if async_download:
            t = threading.Thread(
                target=self._do_download, args=(task, on_progress), daemon=True
            )
            t.start()
            return task.task_id
        return self._do_download(task, on_progress)

    def _create_task(self, url: str, filename: Optional[str], category_folder: bool) -> DownloadTask:
        self._task_counter += 1
        task_id = f"dl_{self._task_counter}"
        fname = filename or Path(urlparse(url).path).name or f"download_{task_id}"
        ext = Path(fname).suffix.lower()
        if category_folder:
            category = self._get_category(ext)
            dest_dir = self.downloads_dir / category
        else:
            dest_dir = self.downloads_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = str(dest_dir / fname)
        task = DownloadTask(task_id, url, dest_path)
        self._tasks[task_id] = task
        return task

    def _do_download(self, task: DownloadTask, on_progress: Optional[Callable] = None) -> Optional[str]:
        """Perform the actual download."""
        try:
            import requests
            task.status = "downloading"
            task.started_at = datetime.now().isoformat()

            # Avoid duplicate downloads
            if os.path.exists(task.dest_path):
                base, ext = os.path.splitext(task.dest_path)
                task.dest_path = f"{base}_{task.task_id}{ext}"

            with requests.get(task.url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                task.total_bytes = total
                downloaded = 0

                with open(task.dest_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            task.downloaded_bytes = downloaded
                            if total > 0:
                                task.progress = round(downloaded / total * 100, 1)
                                if on_progress:
                                    on_progress(task.progress)

            task.status = "completed"
            task.progress = 100
            task.finished_at = datetime.now().isoformat()
            logger.info(f"Download complete: {task.dest_path}")
            return task.dest_path

        except ImportError:
            task.status = "failed"
            task.error = "requests library not available"
            return None
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"Download failed for {task.url}: {e}")
            return None

    def _get_category(self, extension: str) -> str:
        for category, exts in self.CATEGORY_EXTENSIONS.items():
            if extension in exts:
                return category
        return "Other"

    def get_task(self, task_id: str) -> Optional[Dict]:
        task = self._tasks.get(task_id)
        if task:
            return task.__dict__
        return None

    def get_all_tasks(self) -> List[Dict]:
        return [t.__dict__ for t in self._tasks.values()]

    def clear_completed(self) -> int:
        completed = [tid for tid, t in self._tasks.items() if t.status == "completed"]
        for tid in completed:
            del self._tasks[tid]
        return len(completed)
