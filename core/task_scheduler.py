"""
Task Scheduler - Background job scheduling for Jarvis AI.
"""

import logging
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

from utils.config import Config

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Wrapper around APScheduler for managing background tasks."""

    def __init__(self, config: Config, db=None):
        self.config = config
        self.db = db
        self._scheduler = None
        self._jobs: Dict[str, Dict] = {}
        self._running = False

        if APSCHEDULER_AVAILABLE:
            self._scheduler = BackgroundScheduler(
                timezone=config.get("scheduler.timezone", "UTC")
            )
        else:
            logger.warning("APScheduler not installed — scheduler disabled")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start the background scheduler."""
        if self._scheduler and not self._running:
            self._scheduler.start()
            self._running = True
            logger.info("Task scheduler started")

    def stop(self):
        """Stop the scheduler gracefully."""
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Task scheduler stopped")

    # ------------------------------------------------------------------
    # Job Management
    # ------------------------------------------------------------------

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        name: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Add a job that runs at a fixed interval."""
        if not self._scheduler:
            return False
        try:
            self._scheduler.add_job(
                func,
                trigger=IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds),
                id=job_id,
                name=name or job_id,
                replace_existing=True,
                kwargs=kwargs,
            )
            self._jobs[job_id] = {
                "id": job_id,
                "name": name or job_id,
                "type": "interval",
                "added_at": datetime.now().isoformat(),
            }
            logger.info(f"Added interval job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"add_interval_job failed: {e}")
            return False

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        cron_expression: str,
        name: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Add a cron-style job.
        cron_expression format: 'minute hour day month day_of_week'
        Example: '0 9 * * 1-5' for weekdays at 9 AM.
        """
        if not self._scheduler:
            return False
        try:
            parts = cron_expression.strip().split()
            if len(parts) != 5:
                raise ValueError("Cron expression must have 5 parts")
            minute, hour, day, month, day_of_week = parts
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
            )
            self._scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                name=name or job_id,
                replace_existing=True,
                kwargs=kwargs,
            )
            self._jobs[job_id] = {
                "id": job_id,
                "name": name or job_id,
                "type": "cron",
                "cron": cron_expression,
                "added_at": datetime.now().isoformat(),
            }
            logger.info(f"Added cron job: {job_id} ({cron_expression})")
            return True
        except Exception as e:
            logger.error(f"add_cron_job failed: {e}")
            return False

    def add_one_time_job(
        self,
        func: Callable,
        job_id: str,
        run_at: datetime,
        name: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Schedule a one-time job."""
        if not self._scheduler:
            return False
        try:
            self._scheduler.add_job(
                func,
                trigger=DateTrigger(run_date=run_at),
                id=job_id,
                name=name or job_id,
                replace_existing=True,
                kwargs=kwargs,
            )
            self._jobs[job_id] = {
                "id": job_id,
                "name": name or job_id,
                "type": "one_time",
                "run_at": run_at.isoformat(),
                "added_at": datetime.now().isoformat(),
            }
            logger.info(f"Added one-time job: {job_id} at {run_at}")
            return True
        except Exception as e:
            logger.error(f"add_one_time_job failed: {e}")
            return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        if not self._scheduler:
            return False
        try:
            self._scheduler.remove_job(job_id)
            self._jobs.pop(job_id, None)
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"remove_job failed: {e}")
            return False

    def get_jobs(self) -> List[Dict]:
        """Return all scheduled jobs."""
        if not self._scheduler:
            return []
        jobs = []
        for job in self._scheduler.get_jobs():
            info = self._jobs.get(job.id, {})
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "type": info.get("type", "unknown"),
                }
            )
        return jobs

    def is_running(self) -> bool:
        return self._running
