"""
Machine Learning Models - Predictive analytics and pattern recognition.
"""

import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class MLModels:
    """
    Collection of lightweight ML models for:
    - Task classification
    - Usage pattern analysis
    - Time-series forecasting (simple heuristics when scikit-learn unavailable)
    - Anomaly detection
    """

    def __init__(self, config, db=None):
        self.config = config
        self.db = db
        self.models_dir = config.get("paths.models", "models")
        os.makedirs(self.models_dir, exist_ok=True)

        self._task_counts: Counter = Counter()
        self._hourly_usage: defaultdict = defaultdict(int)
        self._category_model = None
        self._sklearn_available = self._check_sklearn()

    # ------------------------------------------------------------------
    # Intent / category classification
    # ------------------------------------------------------------------

    def classify_task(self, text: str) -> Dict:
        """Classify a text into a task category with confidence."""
        keywords = {
            "file_ops": ["file", "folder", "directory", "create", "delete", "move", "copy", "rename", "open"],
            "system_control": ["cpu", "ram", "memory", "process", "kill", "start", "system", "disk", "monitor"],
            "web_search": ["search", "google", "find", "look up", "browse", "web", "internet"],
            "calendar": ["schedule", "meeting", "reminder", "appointment", "calendar", "event", "date"],
            "email": ["email", "mail", "send", "inbox", "message", "compose"],
            "analytics": ["report", "analyze", "stats", "statistics", "chart", "graph", "data"],
            "automation": ["automate", "workflow", "trigger", "routine", "schedule", "batch"],
            "knowledge": ["explain", "what is", "how to", "define", "describe", "summarize"],
        }
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        for category, words in keywords.items():
            scores[category] = sum(1 for w in words if w in text_lower)

        best = max(scores, key=scores.get)
        total = sum(scores.values()) or 1
        confidence = round(scores[best] / total, 2) if scores[best] > 0 else 0.1
        return {"category": best if scores[best] > 0 else "general", "confidence": confidence, "scores": scores}

    # ------------------------------------------------------------------
    # Pattern / behavior analysis
    # ------------------------------------------------------------------

    def record_usage(self, command: str, category: str, hour: int = None):
        """Record a command usage event for pattern learning."""
        self._task_counts[category] += 1
        h = hour if hour is not None else datetime.now().hour
        self._hourly_usage[h] += 1

    def predict_next_task(self, current_category: str) -> Optional[str]:
        """Predict the most likely next task based on history."""
        if not self._task_counts:
            return None
        # Return the globally most-used category (simple baseline)
        most_common = self._task_counts.most_common(3)
        for cat, _ in most_common:
            if cat != current_category:
                return cat
        return most_common[0][0] if most_common else None

    def get_peak_hours(self) -> List[int]:
        """Return the top-3 hours with most activity."""
        if not self._hourly_usage:
            return []
        return [h for h, _ in sorted(self._hourly_usage.items(), key=lambda x: -x[1])[:3]]

    # ------------------------------------------------------------------
    # Anomaly detection (simple z-score)
    # ------------------------------------------------------------------

    def detect_anomaly(self, values: List[float], threshold: float = 2.5) -> List[bool]:
        """
        Detect anomalies using z-score method.
        Returns a boolean mask (True = anomaly).
        """
        if len(values) < 3:
            return [False] * len(values)
        try:
            import statistics
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            if stdev == 0:
                return [False] * len(values)
            return [abs(v - mean) / stdev > threshold for v in values]
        except Exception:
            return [False] * len(values)

    # ------------------------------------------------------------------
    # Simple time-series forecast
    # ------------------------------------------------------------------

    def forecast(self, values: List[float], steps: int = 3) -> List[float]:
        """
        Simple moving-average forecast for the next `steps` points.
        Uses scikit-learn LinearRegression when available.
        """
        if not values:
            return []
        window = min(5, len(values))
        if self._sklearn_available:
            return self._lr_forecast(values, steps)
        # Fallback: linear extrapolation from last window
        recent = values[-window:]
        avg_delta = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
        last = recent[-1]
        return [round(last + avg_delta * (i + 1), 4) for i in range(steps)]

    def _lr_forecast(self, values: List[float], steps: int) -> List[float]:
        """Linear regression forecast using scikit-learn."""
        try:
            from sklearn.linear_model import LinearRegression
            import numpy as np

            X = np.arange(len(values)).reshape(-1, 1)
            y = np.array(values)
            model = LinearRegression()
            model.fit(X, y)
            future = np.arange(len(values), len(values) + steps).reshape(-1, 1)
            return [round(float(v), 4) for v in model.predict(future)]
        except Exception as e:
            logger.warning(f"LR forecast failed: {e}")
            return self.forecast.__wrapped__(values, steps) if hasattr(self.forecast, "__wrapped__") else []

    # ------------------------------------------------------------------
    # Model persistence
    # ------------------------------------------------------------------

    def save_state(self):
        """Persist learned state to disk."""
        state = {
            "task_counts": dict(self._task_counts),
            "hourly_usage": dict(self._hourly_usage),
            "saved_at": datetime.now().isoformat(),
        }
        path = os.path.join(self.models_dir, "ml_state.json")
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        """Load persisted state from disk."""
        path = os.path.join(self.models_dir, "ml_state.json")
        if not os.path.exists(path):
            return
        with open(path) as f:
            state = json.load(f)
        self._task_counts = Counter(state.get("task_counts", {}))
        self._hourly_usage = defaultdict(int, {int(k): v for k, v in state.get("hourly_usage", {}).items()})

    # ------------------------------------------------------------------

    @staticmethod
    def _check_sklearn() -> bool:
        try:
            import sklearn  # noqa: F401
            return True
        except ImportError:
            return False
