"""
Smart Scheduler - Intelligent task scheduling with conflict detection.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytz

from utils.config import Config

logger = logging.getLogger(__name__)


class SmartScheduler:
    """
    Advanced scheduling with:
    - Conflict detection
    - Time zone handling
    - Priority-based ordering
    - Optimal time suggestions
    - Deadline tracking
    """

    PRIORITY_MAP = {"critical": 4, "high": 3, "medium": 2, "low": 1}

    def __init__(self, config: Config, db=None):
        self.config = config
        self.db = db
        self.timezone = config.get("scheduler.timezone", "UTC")
        self._tasks: List[Dict] = []

    # ------------------------------------------------------------------
    # Task Management
    # ------------------------------------------------------------------

    def add_task(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int = 60,
        priority: str = "medium",
        deadline: Optional[datetime] = None,
        recurrence: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict:
        """Add a scheduled task."""
        task = {
            "id": f"task_{len(self._tasks) + 1}_{int(start_time.timestamp())}",
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(minutes=duration_minutes)).isoformat(),
            "duration_minutes": duration_minutes,
            "priority": priority,
            "priority_score": self.PRIORITY_MAP.get(priority, 2),
            "deadline": deadline.isoformat() if deadline else None,
            "recurrence": recurrence,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "status": "scheduled",
        }

        # Check for conflicts
        conflicts = self.detect_conflicts(start_time, duration_minutes, exclude_id=task["id"])
        if conflicts:
            task["conflicts"] = [c["title"] for c in conflicts]
            logger.warning(f"Task '{title}' has conflicts: {task['conflicts']}")

        self._tasks.append(task)
        logger.info(f"Task scheduled: {title} at {start_time}")
        return task

    def detect_conflicts(
        self,
        start_time: datetime,
        duration_minutes: int,
        exclude_id: Optional[str] = None,
    ) -> List[Dict]:
        """Return tasks that overlap with the given time window."""
        end_time = start_time + timedelta(minutes=duration_minutes)
        conflicts = []
        for task in self._tasks:
            if task["id"] == exclude_id:
                continue
            if task["status"] in ("completed", "cancelled"):
                continue
            task_start = datetime.fromisoformat(task["start_time"])
            task_end = datetime.fromisoformat(task["end_time"])
            if task_start < end_time and task_end > start_time:
                conflicts.append(task)
        return conflicts

    def get_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> List[Dict]:
        """Query tasks with optional filters."""
        tasks = list(self._tasks)
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        if priority:
            tasks = [t for t in tasks if t["priority"] == priority]
        if date:
            date_str = date.strftime("%Y-%m-%d")
            tasks = [t for t in tasks if t["start_time"].startswith(date_str)]
        return sorted(tasks, key=lambda t: (-(t["priority_score"]), t["start_time"]))

    def complete_task(self, task_id: str) -> bool:
        for task in self._tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["completed_at"] = datetime.now().isoformat()
                return True
        return False

    def cancel_task(self, task_id: str) -> bool:
        for task in self._tasks:
            if task["id"] == task_id:
                task["status"] = "cancelled"
                return True
        return False

    # ------------------------------------------------------------------
    # Intelligent Scheduling
    # ------------------------------------------------------------------

    def suggest_time(
        self,
        duration_minutes: int = 60,
        from_time: Optional[datetime] = None,
        working_hours: tuple = (9, 17),
    ) -> Optional[datetime]:
        """Suggest the next available time slot with no conflicts."""
        start = from_time or datetime.now().replace(second=0, microsecond=0)
        # Round up to next 15-minute slot
        minutes = (start.minute // 15 + 1) * 15
        if minutes >= 60:
            start = start.replace(hour=start.hour + 1, minute=0)
        else:
            start = start.replace(minute=minutes)

        # Try the next 48 hours
        for _ in range(48 * 4):  # 15-min increments
            if working_hours[0] <= start.hour < working_hours[1]:
                conflicts = self.detect_conflicts(start, duration_minutes)
                if not conflicts:
                    return start
            start += timedelta(minutes=15)

        return None

    def get_overdue_tasks(self) -> List[Dict]:
        """Return tasks past their deadline that are not completed."""
        now = datetime.now().isoformat()
        return [
            t for t in self._tasks
            if t.get("deadline") and t["deadline"] < now and t["status"] == "scheduled"
        ]

    def get_today_agenda(self) -> List[Dict]:
        """Return all tasks scheduled for today."""
        return self.get_tasks(date=datetime.now())

    def convert_timezone(self, dt: datetime, target_tz: str) -> datetime:
        """Convert a datetime to a target timezone."""
        try:
            tz = pytz.timezone(target_tz)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            return dt.astimezone(tz)
        except Exception as e:
            logger.warning(f"Timezone conversion failed: {e}")
            return dt
