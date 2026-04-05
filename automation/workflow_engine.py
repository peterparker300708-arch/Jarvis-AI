"""
Workflow Engine - Chain multiple tasks and create automated workflows.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class WorkflowStep:
    """A single step in a workflow."""

    def __init__(
        self,
        name: str,
        action: Callable,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None,
        condition: Optional[Callable] = None,
        on_error: str = "stop",  # stop | continue | retry
        retry_count: int = 0,
    ):
        self.name = name
        self.action = action
        self.args = args or []
        self.kwargs = kwargs or {}
        self.condition = condition
        self.on_error = on_error
        self.retry_count = retry_count


class WorkflowResult:
    """Result of a workflow execution."""

    def __init__(self, workflow_id: str, workflow_name: str):
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.steps: List[Dict] = []
        self.success = True
        self.started_at = datetime.now().isoformat()
        self.finished_at: Optional[str] = None
        self.error: Optional[str] = None

    def add_step_result(self, name: str, success: bool, output: Any, error: Optional[str] = None):
        self.steps.append(
            {
                "name": name,
                "success": success,
                "output": str(output)[:500] if output is not None else None,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if not success:
            self.success = False

    def finalize(self):
        self.finished_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "success": self.success,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "steps": self.steps,
            "error": self.error,
        }


class WorkflowEngine:
    """
    Execute multi-step workflows with:
    - Conditional execution
    - Error handling
    - Retry logic
    - Step chaining
    """

    def __init__(self, config: Config, db=None):
        self.config = config
        self.db = db
        self._workflows: Dict[str, Dict] = {}
        self._history: List[Dict] = []

    # ------------------------------------------------------------------
    # Workflow Management
    # ------------------------------------------------------------------

    def register_workflow(
        self,
        workflow_id: str,
        name: str,
        steps: List[WorkflowStep],
        description: str = "",
    ) -> bool:
        """Register a workflow for later execution."""
        self._workflows[workflow_id] = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
        }
        logger.info(f"Registered workflow: {workflow_id} ({name})")
        return True

    def execute(self, workflow_id: str, context: Optional[Dict] = None) -> WorkflowResult:
        """Execute a registered workflow."""
        if workflow_id not in self._workflows:
            result = WorkflowResult(workflow_id, "unknown")
            result.error = f"Workflow '{workflow_id}' not found"
            result.success = False
            result.finalize()
            return result

        wf = self._workflows[workflow_id]
        result = WorkflowResult(workflow_id, wf["name"])
        logger.info(f"Executing workflow: {workflow_id}")

        for step in wf["steps"]:
            # Evaluate condition
            if step.condition is not None:
                try:
                    should_run = step.condition(context or {})
                except Exception as e:
                    logger.warning(f"Step condition error ({step.name}): {e}")
                    should_run = True

                if not should_run:
                    result.add_step_result(step.name, True, "Skipped (condition not met)")
                    continue

            # Execute step with optional retry
            output = None
            error = None
            success = False

            for attempt in range(max(step.retry_count + 1, 1)):
                try:
                    output = step.action(*step.args, **step.kwargs)
                    success = True
                    break
                except Exception as e:
                    error = str(e)
                    logger.warning(f"Step '{step.name}' attempt {attempt + 1} failed: {e}")
                    if attempt < step.retry_count:
                        time.sleep(1)

            result.add_step_result(step.name, success, output, error)

            if not success and step.on_error == "stop":
                result.error = f"Workflow stopped at step '{step.name}': {error}"
                break

        result.finalize()
        self._history.append(result.to_dict())
        logger.info(f"Workflow {workflow_id} finished (success={result.success})")
        return result

    def execute_steps_inline(self, steps: List[Dict]) -> WorkflowResult:
        """
        Execute an ad-hoc list of step dicts:
        [{"name": ..., "action": callable, "args": [...], "kwargs": {...}}]
        """
        temp_id = f"inline_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        step_objects = []
        for s in steps:
            step_objects.append(
                WorkflowStep(
                    name=s.get("name", "unnamed"),
                    action=s["action"],
                    args=s.get("args", []),
                    kwargs=s.get("kwargs", {}),
                    on_error=s.get("on_error", "continue"),
                )
            )
        self.register_workflow(temp_id, temp_id, step_objects)
        return self.execute(temp_id)

    def get_workflows(self) -> List[Dict]:
        """Return all registered workflows (without step callables)."""
        return [
            {
                "id": wf["id"],
                "name": wf["name"],
                "description": wf["description"],
                "step_count": len(wf["steps"]),
                "created_at": wf["created_at"],
            }
            for wf in self._workflows.values()
        ]

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Return recent workflow execution history."""
        return list(reversed(self._history[-limit:]))
