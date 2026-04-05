"""
Trigger System - IFTTT-style event-based automation for Jarvis AI.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class Trigger:
    """Defines an IFTTT-style trigger."""

    def __init__(
        self,
        trigger_id: str,
        name: str,
        condition: Callable[[], bool],
        action: Callable,
        action_args: Optional[list] = None,
        action_kwargs: Optional[dict] = None,
        cooldown_seconds: int = 60,
        enabled: bool = True,
    ):
        self.trigger_id = trigger_id
        self.name = name
        self.condition = condition
        self.action = action
        self.action_args = action_args or []
        self.action_kwargs = action_kwargs or {}
        self.cooldown_seconds = cooldown_seconds
        self.enabled = enabled
        self._last_fired: Optional[datetime] = None
        self._fire_count = 0


class TriggerSystem:
    """
    Monitor conditions and fire actions when they are met.
    Supports:
    - Custom function-based conditions
    - Time-based conditions
    - System metric conditions
    - Cooldown periods to prevent spam
    """

    def __init__(self, config: Config):
        self.config = config
        self._triggers: Dict[str, Trigger] = {}
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._check_interval = 5  # seconds

    # ------------------------------------------------------------------
    # Trigger Management
    # ------------------------------------------------------------------

    def register(
        self,
        trigger_id: str,
        name: str,
        condition: Callable[[], bool],
        action: Callable,
        action_args: Optional[list] = None,
        action_kwargs: Optional[dict] = None,
        cooldown_seconds: int = 60,
    ) -> bool:
        """Register a new trigger."""
        self._triggers[trigger_id] = Trigger(
            trigger_id=trigger_id,
            name=name,
            condition=condition,
            action=action,
            action_args=action_args,
            action_kwargs=action_kwargs,
            cooldown_seconds=cooldown_seconds,
        )
        logger.info(f"Trigger registered: {trigger_id} ({name})")
        return True

    def remove(self, trigger_id: str) -> bool:
        """Remove a trigger."""
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            logger.info(f"Trigger removed: {trigger_id}")
            return True
        return False

    def enable(self, trigger_id: str):
        """Enable a trigger."""
        if trigger_id in self._triggers:
            self._triggers[trigger_id].enabled = True

    def disable(self, trigger_id: str):
        """Disable a trigger without removing it."""
        if trigger_id in self._triggers:
            self._triggers[trigger_id].enabled = False

    # ------------------------------------------------------------------
    # Monitoring Loop
    # ------------------------------------------------------------------

    def start(self):
        """Start monitoring triggers in a background thread."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="trigger-monitor"
        )
        self._monitor_thread.start()
        logger.info(f"Trigger monitor started ({len(self._triggers)} triggers)")

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        logger.info("Trigger monitor stopped")

    def _monitor_loop(self):
        while self._running:
            self._check_triggers()
            time.sleep(self._check_interval)

    def _check_triggers(self):
        """Evaluate all triggers and fire if conditions are met."""
        for trigger in list(self._triggers.values()):
            if not trigger.enabled:
                continue

            # Enforce cooldown
            if trigger._last_fired:
                elapsed = (datetime.now() - trigger._last_fired).total_seconds()
                if elapsed < trigger.cooldown_seconds:
                    continue

            try:
                if trigger.condition():
                    logger.info(f"Trigger fired: {trigger.trigger_id}")
                    trigger._last_fired = datetime.now()
                    trigger._fire_count += 1
                    threading.Thread(
                        target=trigger.action,
                        args=trigger.action_args,
                        kwargs=trigger.action_kwargs,
                        daemon=True,
                    ).start()
            except Exception as e:
                logger.warning(f"Trigger condition error ({trigger.trigger_id}): {e}")

    # ------------------------------------------------------------------
    # Utility: Pre-built Conditions
    # ------------------------------------------------------------------

    @staticmethod
    def cpu_above(threshold: float = 90.0) -> Callable[[], bool]:
        """Returns a condition function that fires when CPU > threshold."""
        def condition():
            try:
                import psutil
                return psutil.cpu_percent(interval=0.1) > threshold
            except Exception:
                return False
        return condition

    @staticmethod
    def ram_above(threshold: float = 90.0) -> Callable[[], bool]:
        def condition():
            try:
                import psutil
                return psutil.virtual_memory().percent > threshold
            except Exception:
                return False
        return condition

    @staticmethod
    def time_is(hour: int, minute: int = 0) -> Callable[[], bool]:
        """Returns a condition that fires at a specific time."""
        def condition():
            now = datetime.now()
            return now.hour == hour and now.minute == minute
        return condition

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_triggers(self) -> List[Dict]:
        """Return all registered triggers as dicts."""
        return [
            {
                "id": t.trigger_id,
                "name": t.name,
                "enabled": t.enabled,
                "fire_count": t._fire_count,
                "last_fired": t._last_fired.isoformat() if t._last_fired else None,
                "cooldown_seconds": t.cooldown_seconds,
            }
            for t in self._triggers.values()
        ]

    def is_running(self) -> bool:
        return self._running
