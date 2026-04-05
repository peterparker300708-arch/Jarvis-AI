"""
Tutorial System - Interactive learning tutorials for Jarvis AI.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)

# Built-in tutorial library
TUTORIAL_CATALOG = {
    "jarvis-basics": {
        "title": "Jarvis AI Basics",
        "description": "Learn the fundamentals of using Jarvis AI",
        "difficulty": "beginner",
        "duration_minutes": 10,
        "steps": [
            {
                "title": "Starting Jarvis",
                "content": "Run `python jarvis.py` to start in CLI mode. Use `--mode web` for the web dashboard.",
                "exercise": "Start Jarvis and type 'Hello'.",
                "expected": "A greeting response from Jarvis.",
            },
            {
                "title": "Getting System Status",
                "content": "Type 'status' to see your system's current resource usage.",
                "exercise": "Check your current CPU and RAM usage.",
                "expected": "A report showing CPU %, RAM %, and Disk % usage.",
            },
            {
                "title": "Saving Notes",
                "content": "Type 'note <content>' to save a quick note to the database.",
                "exercise": "Save a note: 'note Remember to review the AI settings'",
                "expected": "Confirmation that the note was saved with an ID.",
            },
            {
                "title": "Asking Questions",
                "content": "Type any natural language question or command to interact with the AI.",
                "exercise": "Ask: 'What is machine learning?'",
                "expected": "An AI-generated explanation of machine learning.",
            },
        ],
    },
    "advanced-commands": {
        "title": "Advanced Jarvis Commands",
        "description": "Master advanced features: workflows, automation, and analytics",
        "difficulty": "intermediate",
        "duration_minutes": 20,
        "steps": [
            {
                "title": "Viewing Command History",
                "content": "Type 'history' to see your recent commands.",
                "exercise": "Check your last 10 commands.",
                "expected": "A list of recent commands with timestamps.",
            },
            {
                "title": "Checking Your Profile",
                "content": "Type 'profile' to see your behavioral analytics.",
                "exercise": "View your behavioral profile.",
                "expected": "Statistics on your command usage, categories, and patterns.",
            },
            {
                "title": "Scheduled Jobs",
                "content": "Type 'jobs' to see all scheduled background tasks.",
                "exercise": "View scheduled jobs.",
                "expected": "A list of active cron jobs and interval tasks.",
            },
            {
                "title": "Using the Web Dashboard",
                "content": "Run `python jarvis.py --mode web` to start the web UI at http://localhost:5000",
                "exercise": "Open the web dashboard and try the chat interface.",
                "expected": "A dark-themed dashboard with chat, system status, and analytics.",
            },
        ],
    },
    "python-basics": {
        "title": "Python Basics for AI Development",
        "description": "Learn Python fundamentals needed for AI programming",
        "difficulty": "beginner",
        "duration_minutes": 30,
        "steps": [
            {
                "title": "Variables and Types",
                "content": "Python has dynamic typing. Variables hold int, float, str, list, dict, bool.",
                "exercise": "Create variables: name='Jarvis', version=2.0, active=True",
                "expected": "No errors, variables assigned successfully.",
            },
            {
                "title": "Functions",
                "content": "Define reusable code with `def function_name(params): ...`",
                "exercise": "Write a function that returns 'Hello, Jarvis!'",
                "expected": "Function returns the greeting string.",
            },
        ],
    },
}


class TutorialSystem:
    """
    Interactive tutorial system with progress tracking.
    """

    def __init__(self, config: Config, db=None):
        self.config = config
        self.db = db
        self._progress: Dict[str, Dict] = {}  # user progress
        self._catalog = dict(TUTORIAL_CATALOG)

    # ------------------------------------------------------------------
    # Tutorial Management
    # ------------------------------------------------------------------

    def list_tutorials(self, difficulty: Optional[str] = None) -> List[Dict]:
        """Return available tutorials with metadata."""
        tutorials = []
        for tid, tut in self._catalog.items():
            if difficulty and tut.get("difficulty") != difficulty:
                continue
            progress = self._progress.get(tid, {})
            tutorials.append(
                {
                    "id": tid,
                    "title": tut["title"],
                    "description": tut["description"],
                    "difficulty": tut.get("difficulty", "beginner"),
                    "duration_minutes": tut.get("duration_minutes", 10),
                    "step_count": len(tut.get("steps", [])),
                    "completed_steps": progress.get("completed_steps", 0),
                    "completed": progress.get("completed", False),
                }
            )
        return tutorials

    def get_tutorial(self, tutorial_id: str) -> Optional[Dict]:
        """Get a tutorial with current progress."""
        tut = self._catalog.get(tutorial_id)
        if not tut:
            return None
        progress = self._progress.get(tutorial_id, {"current_step": 0, "completed_steps": 0})
        current_step_idx = progress.get("current_step", 0)
        steps = tut.get("steps", [])
        current_step = steps[current_step_idx] if current_step_idx < len(steps) else None
        return {
            **tut,
            "id": tutorial_id,
            "current_step_index": current_step_idx,
            "current_step": current_step,
            "total_steps": len(steps),
            "progress_percent": round(progress.get("completed_steps", 0) / max(len(steps), 1) * 100),
        }

    def start_tutorial(self, tutorial_id: str) -> Dict:
        """Start or restart a tutorial."""
        if tutorial_id not in self._catalog:
            return {"error": f"Tutorial '{tutorial_id}' not found"}
        self._progress[tutorial_id] = {
            "current_step": 0,
            "completed_steps": 0,
            "started_at": datetime.now().isoformat(),
            "completed": False,
        }
        return self.get_tutorial(tutorial_id)

    def complete_step(self, tutorial_id: str) -> Dict:
        """Mark the current step as complete and advance to the next."""
        tut = self._catalog.get(tutorial_id)
        if not tut:
            return {"error": "Tutorial not found"}
        progress = self._progress.setdefault(
            tutorial_id, {"current_step": 0, "completed_steps": 0, "completed": False}
        )
        total = len(tut.get("steps", []))
        current = progress["current_step"]
        if current < total:
            progress["completed_steps"] += 1
            progress["current_step"] = min(current + 1, total)
        if progress["current_step"] >= total:
            progress["completed"] = True
            progress["completed_at"] = datetime.now().isoformat()
        return self.get_tutorial(tutorial_id)

    def add_tutorial(self, tutorial_id: str, tutorial: Dict) -> bool:
        """Add a custom tutorial to the catalog."""
        self._catalog[tutorial_id] = tutorial
        logger.info(f"Tutorial added: {tutorial_id}")
        return True

    def get_user_stats(self) -> Dict:
        """Return learning statistics."""
        completed = sum(1 for p in self._progress.values() if p.get("completed"))
        in_progress = sum(1 for p in self._progress.values() if not p.get("completed") and p.get("completed_steps", 0) > 0)
        return {
            "total_tutorials": len(self._catalog),
            "completed": completed,
            "in_progress": in_progress,
            "not_started": len(self._catalog) - completed - in_progress,
        }
