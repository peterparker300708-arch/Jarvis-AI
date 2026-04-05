"""
Routine Manager - Custom morning/evening/work routines for Jarvis AI.
"""

import json
import logging
import os
from datetime import datetime
from typing import Callable, Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)

# Built-in routine templates
ROUTINE_TEMPLATES = {
    "morning": {
        "name": "Morning Routine",
        "trigger_hour": 7,
        "steps": [
            "Get daily news briefing",
            "Check calendar for today",
            "Review pending tasks",
            "Check system health",
            "Get weather forecast",
        ],
    },
    "evening": {
        "name": "Evening Routine",
        "trigger_hour": 18,
        "steps": [
            "Summarize today's activities",
            "Schedule tomorrow's tasks",
            "Backup important files",
            "Clear temporary files",
            "Send daily report",
        ],
    },
    "work_start": {
        "name": "Work Start Routine",
        "trigger_hour": 9,
        "steps": [
            "Check emails",
            "Review project tasks",
            "Check team notifications",
            "Start focus timer",
        ],
    },
    "work_end": {
        "name": "Work End Routine",
        "trigger_hour": 17,
        "steps": [
            "Save all work",
            "Log completed tasks",
            "Set reminders for tomorrow",
            "Generate work summary",
        ],
    },
    "weekly_review": {
        "name": "Weekly Review",
        "trigger_hour": 10,
        "steps": [
            "Generate weekly analytics report",
            "Review completed tasks",
            "Plan next week priorities",
            "Clean up downloads folder",
            "Archive old files",
        ],
    },
}


class Routine:
    def __init__(self, routine_id: str, name: str, trigger_hour: int, steps: List[str]):
        self.routine_id = routine_id
        self.name = name
        self.trigger_hour = trigger_hour
        self.steps = steps
        self.enabled = True
        self.last_run: Optional[str] = None
        self.run_count = 0
        self._step_functions: Dict[str, Callable] = {}


class RoutineManager:
    """Manage and execute automated routines."""

    def __init__(self, config: Config, db=None, scheduler=None):
        self.config = config
        self.db = db
        self.scheduler = scheduler
        self._routines: Dict[str, Routine] = {}
        self._load_templates()

    def _load_templates(self):
        """Load built-in routine templates."""
        for rid, template in ROUTINE_TEMPLATES.items():
            routine = Routine(
                routine_id=rid,
                name=template["name"],
                trigger_hour=template["trigger_hour"],
                steps=template["steps"],
            )
            self._routines[rid] = routine

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_routine(
        self,
        routine_id: str,
        name: str,
        trigger_hour: int,
        steps: List[str],
    ) -> Routine:
        """Create and register a custom routine."""
        routine = Routine(routine_id, name, trigger_hour, steps)
        self._routines[routine_id] = routine
        logger.info(f"Routine created: {routine_id} ({name}) at {trigger_hour:02d}:00")
        return routine

    def delete_routine(self, routine_id: str) -> bool:
        if routine_id in self._routines:
            del self._routines[routine_id]
            return True
        return False

    def get_routine(self, routine_id: str) -> Optional[Routine]:
        return self._routines.get(routine_id)

    def list_routines(self) -> List[Dict]:
        return [
            {
                "id": r.routine_id,
                "name": r.name,
                "trigger_hour": r.trigger_hour,
                "steps": r.steps,
                "enabled": r.enabled,
                "last_run": r.last_run,
                "run_count": r.run_count,
            }
            for r in self._routines.values()
        ]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_routine(self, routine_id: str) -> Dict:
        """Execute a routine and return its result."""
        routine = self._routines.get(routine_id)
        if not routine:
            return {"success": False, "error": f"Routine '{routine_id}' not found"}

        results = []
        for step in routine.steps:
            # Try to call a registered function, otherwise log as text step
            func = routine._step_functions.get(step)
            if func:
                try:
                    output = func()
                    results.append({"step": step, "success": True, "output": str(output)[:200]})
                except Exception as e:
                    results.append({"step": step, "success": False, "error": str(e)})
            else:
                results.append({"step": step, "success": True, "output": "(manual step)"})

        routine.last_run = datetime.now().isoformat()
        routine.run_count += 1

        return {
            "success": True,
            "routine_id": routine_id,
            "name": routine.name,
            "steps_executed": len(results),
            "results": results,
            "timestamp": routine.last_run,
        }

    def register_step_function(self, routine_id: str, step_name: str, func: Callable):
        """Bind an actual callable to a step within a routine."""
        routine = self._routines.get(routine_id)
        if routine:
            routine._step_functions[step_name] = func

    # ------------------------------------------------------------------
    # Schedule All Routines
    # ------------------------------------------------------------------

    def schedule_all(self):
        """Register all enabled routines with the task scheduler."""
        if not self.scheduler:
            logger.warning("No scheduler available — routines not scheduled")
            return

        for routine in self._routines.values():
            if routine.enabled:
                cron = f"0 {routine.trigger_hour} * * *"
                self.scheduler.add_cron_job(
                    func=self.execute_routine,
                    job_id=f"routine_{routine.routine_id}",
                    cron_expression=cron,
                    name=routine.name,
                    routine_id=routine.routine_id,
                )
                logger.info(f"Scheduled routine '{routine.routine_id}' at {routine.trigger_hour:02d}:00")

    def check_due_routines(self) -> List[str]:
        """Return IDs of routines that are due to run at the current hour."""
        current_hour = datetime.now().hour
        due = []
        for routine in self._routines.values():
            if routine.enabled and routine.trigger_hour == current_hour:
                if routine.last_run:
                    last = datetime.fromisoformat(routine.last_run)
                    if (datetime.now() - last).total_seconds() < 3600:
                        continue
                due.append(routine.routine_id)
        return due
