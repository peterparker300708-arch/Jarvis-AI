"""Task scheduler wrapping APScheduler with a database-persisted task registry."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# APScheduler optional import guard
# ---------------------------------------------------------------------------

try:
    from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import]
    from apscheduler.triggers.date import DateTrigger  # type: ignore[import]
    from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import]
    from apscheduler.triggers.cron import CronTrigger  # type: ignore[import]
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR  # type: ignore[import]
    _APS_AVAILABLE = True
except ImportError:
    _APS_AVAILABLE = False
    logger.warning(
        "APScheduler not installed — task scheduling disabled. "
        "Install with: pip install apscheduler"
    )


class TaskScheduler:
    """Manages scheduled and recurring tasks using APScheduler.

    When APScheduler is not installed the scheduler enters a no-op mode; all
    public methods are still callable and return graceful error dicts.

    Args:
        db_manager: Optional :class:`~database.db_manager.DatabaseManager`
            instance used to persist task metadata.
        timezone: Scheduler timezone string (default ``"UTC"``).
        max_instances: Maximum concurrent instances of a single job.
        coalesce: If ``True``, merge missed executions into one.
    """

    def __init__(
        self,
        db_manager=None,
        timezone: str = "UTC",
        max_instances: int = 3,
        coalesce: bool = True,
    ) -> None:
        self._db = db_manager
        self._timezone = timezone
        self._max_instances = max_instances
        self._coalesce = coalesce
        self._scheduler: Any = None
        self._lock = threading.Lock()
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Start the scheduler.

        Returns:
            ``True`` on success, ``False`` if APScheduler is unavailable or
            the scheduler is already running.
        """
        if not _APS_AVAILABLE:
            logger.error("APScheduler not installed — cannot start scheduler.")
            return False
        with self._lock:
            if self._running:
                logger.warning("Scheduler is already running.")
                return False
            self._scheduler = BackgroundScheduler(
                timezone=self._timezone,
                job_defaults={
                    "coalesce": self._coalesce,
                    "max_instances": self._max_instances,
                    "misfire_grace_time": 60,
                },
            )
            self._scheduler.add_listener(
                self._on_job_executed, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
            )
            self._scheduler.start()
            self._running = True
            logger.info("Task scheduler started (timezone=%s).", self._timezone)
        return True

    def stop(self, wait: bool = True) -> None:
        """Stop the scheduler.

        Args:
            wait: If ``True``, wait for running jobs to finish.
        """
        with self._lock:
            if self._scheduler and self._running:
                self._scheduler.shutdown(wait=wait)
                self._running = False
                logger.info("Task scheduler stopped.")

    @property
    def is_running(self) -> bool:
        """``True`` if the scheduler is currently active."""
        return self._running

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def add_task(
        self,
        name: str,
        func: Callable,
        trigger: str,
        job_id: Optional[str] = None,
        replace_existing: bool = True,
        **trigger_kwargs,
    ) -> dict[str, Any]:
        """Add a job to the scheduler.

        Args:
            name: Human-readable task name.
            func: Python callable to execute.
            trigger: Trigger type: ``"date"``, ``"interval"``, or ``"cron"``.
            job_id: Explicit job ID (defaults to *name*).
            replace_existing: If ``True``, overwrite an existing job with the
                same ID rather than raising an error.
            **trigger_kwargs: Passed directly to the APScheduler trigger.

        Returns:
            Dict with ``success``, ``job_id``, and ``message`` keys.
        """
        if not self._running:
            return {"success": False, "job_id": None, "message": "Scheduler is not running."}

        jid = job_id or name.replace(" ", "_")
        try:
            self._scheduler.add_job(
                func,
                trigger,
                id=jid,
                name=name,
                replace_existing=replace_existing,
                **trigger_kwargs,
            )
            self._persist_task(name, trigger, trigger_kwargs)
            logger.info("Task added: %r (trigger=%s)", name, trigger)
            return {"success": True, "job_id": jid, "message": f"Task '{name}' scheduled."}
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to add task %r: %s", name, exc)
            return {"success": False, "job_id": None, "message": str(exc)}

    def remove_task(self, task_id: str) -> dict[str, Any]:
        """Remove a scheduled task by ID.

        Args:
            task_id: Job ID string.

        Returns:
            Dict with ``success`` and ``message`` keys.
        """
        if not self._running:
            return {"success": False, "message": "Scheduler is not running."}
        try:
            self._scheduler.remove_job(task_id)
            logger.info("Task removed: %r", task_id)
            return {"success": True, "message": f"Task '{task_id}' removed."}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "message": str(exc)}

    def pause_task(self, task_id: str) -> dict[str, Any]:
        """Pause a task without removing it."""
        if not self._running:
            return {"success": False, "message": "Scheduler is not running."}
        try:
            self._scheduler.pause_job(task_id)
            return {"success": True, "message": f"Task '{task_id}' paused."}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "message": str(exc)}

    def resume_task(self, task_id: str) -> dict[str, Any]:
        """Resume a previously paused task."""
        if not self._running:
            return {"success": False, "message": "Scheduler is not running."}
        try:
            self._scheduler.resume_job(task_id)
            return {"success": True, "message": f"Task '{task_id}' resumed."}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "message": str(exc)}

    def list_tasks(self) -> List[dict[str, Any]]:
        """Return metadata for all currently scheduled jobs.

        Returns:
            List of dicts with ``id``, ``name``, ``next_run``, ``trigger``
            and ``pending`` fields.
        """
        if not self._running or self._scheduler is None:
            return []
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "pending": job.pending,
            })
        return jobs

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def schedule_reminder(
        self,
        reminder_id: int,
        message: str,
        run_at: datetime,
    ) -> dict[str, Any]:
        """Schedule a one-shot reminder notification.

        Args:
            reminder_id: Database ID of the reminder record.
            message: Human-readable reminder message to announce.
            run_at: UTC datetime at which the reminder should fire.

        Returns:
            Dict with ``success``, ``job_id``, and ``message`` keys.
        """
        def _fire_reminder():
            logger.info("REMINDER [%d]: %s", reminder_id, message)
            print(f"\n🔔 REMINDER: {message}\n")
            if self._db is not None:
                try:
                    self._db.complete_reminder(reminder_id)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Could not mark reminder %d complete: %s", reminder_id, exc)

        jid = f"reminder_{reminder_id}"
        return self.add_task(
            name=f"Reminder #{reminder_id}",
            func=_fire_reminder,
            trigger="date",
            job_id=jid,
            run_date=run_at,
        )

    def schedule_recurring(
        self,
        name: str,
        func: Callable,
        interval_minutes: int,
        job_id: Optional[str] = None,
        start_immediately: bool = False,
    ) -> dict[str, Any]:
        """Add a recurring task that runs every *interval_minutes* minutes.

        Args:
            name: Human-readable task name.
            func: Callable to execute on each interval.
            interval_minutes: Recurrence interval in minutes.
            job_id: Explicit job ID override.
            start_immediately: If ``True``, execute once right away before
                scheduling the interval.

        Returns:
            Dict with ``success``, ``job_id``, and ``message`` keys.
        """
        if start_immediately:
            try:
                func()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Immediate execution of %r raised: %s", name, exc)

        start_date = datetime.utcnow() + timedelta(minutes=interval_minutes)
        return self.add_task(
            name=name,
            func=func,
            trigger="interval",
            job_id=job_id,
            minutes=interval_minutes,
            start_date=start_date,
        )

    def schedule_cron(
        self,
        name: str,
        func: Callable,
        job_id: Optional[str] = None,
        **cron_kwargs,
    ) -> dict[str, Any]:
        """Add a task using a cron-style trigger.

        Args:
            name: Human-readable task name.
            func: Callable to execute.
            job_id: Explicit job ID override.
            **cron_kwargs: APScheduler CronTrigger keyword arguments
                (e.g. ``hour=9``, ``minute=0``).

        Returns:
            Dict with ``success``, ``job_id``, and ``message`` keys.
        """
        return self.add_task(
            name=name,
            func=func,
            trigger="cron",
            job_id=job_id,
            **cron_kwargs,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_job_executed(self, event) -> None:
        """APScheduler event listener — updates ``last_run`` in the database."""
        job_id: str = event.job_id
        if self._db is not None:
            try:
                self._db.record_task_run(job_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not record task run for %r: %s", job_id, exc)

        if hasattr(event, "exception") and event.exception:
            logger.error("Task %r raised: %s", job_id, event.exception)
        else:
            logger.debug("Task %r executed successfully.", job_id)

    def _persist_task(self, name: str, trigger: str, trigger_kwargs: dict) -> None:
        if self._db is None:
            return
        schedule_str = f"{trigger} {trigger_kwargs}"
        try:
            self._db.upsert_task(name=name.replace(" ", "_"), schedule=schedule_str)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not persist task %r: %s", name, exc)
