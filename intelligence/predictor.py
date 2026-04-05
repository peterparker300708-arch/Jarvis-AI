"""
Predictor - Anticipate user needs and take proactive actions.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class Predictor:
    """
    Predicts future user actions and system states:
    - Next likely command
    - System resource exhaustion
    - Optimal times for heavy tasks
    - Routine deviations
    """

    def __init__(self, config: Config, db=None, ml_models=None, behavior_analyzer=None):
        self.config = config
        self.db = db
        self.ml_models = ml_models
        self.behavior_analyzer = behavior_analyzer
        self._prediction_history: List[Dict] = []

    # ------------------------------------------------------------------
    # User Action Prediction
    # ------------------------------------------------------------------

    def predict_next_action(self, current_category: str = "general") -> Optional[Dict]:
        """Predict the user's next most likely action."""
        prediction = None

        if self.ml_models:
            next_cat = self.ml_models.predict_next_task(current_category)
            if next_cat:
                prediction = {
                    "predicted_category": next_cat,
                    "confidence": 0.7,
                    "reason": "Based on your usage patterns",
                    "timestamp": datetime.now().isoformat(),
                }
        elif self.behavior_analyzer:
            profile = self.behavior_analyzer.get_behavioral_profile()
            top = profile.get("top_categories", [])
            if top:
                next_cat = top[0]["category"] if top[0]["category"] != current_category else (
                    top[1]["category"] if len(top) > 1 else None
                )
                if next_cat:
                    prediction = {
                        "predicted_category": next_cat,
                        "confidence": 0.6,
                        "reason": "Frequently used category",
                        "timestamp": datetime.now().isoformat(),
                    }

        if prediction:
            self._prediction_history.append(prediction)
        return prediction

    # ------------------------------------------------------------------
    # System Resource Prediction
    # ------------------------------------------------------------------

    def predict_resource_exhaustion(self, metrics_history: List[Dict]) -> Dict:
        """
        Given a list of historical system metrics, predict when resources
        might be exhausted.
        """
        result: Dict = {}

        if not metrics_history:
            return result

        # Extract CPU and RAM trends
        cpu_values = [m.get("cpu_percent", 0) for m in metrics_history if "cpu_percent" in m]
        ram_values = [m.get("ram_percent", 0) for m in metrics_history if "ram_percent" in m]
        disk_values = [m.get("disk_percent", 0) for m in metrics_history if "disk_percent" in m]

        if self.ml_models and len(cpu_values) >= 3:
            cpu_forecast = self.ml_models.forecast(cpu_values, steps=3)
            ram_forecast = self.ml_models.forecast(ram_values, steps=3) if ram_values else []
            disk_forecast = self.ml_models.forecast(disk_values, steps=3) if disk_values else []
        else:
            cpu_forecast = self._simple_extrapolate(cpu_values, 3)
            ram_forecast = self._simple_extrapolate(ram_values, 3)
            disk_forecast = self._simple_extrapolate(disk_values, 3)

        if cpu_forecast:
            result["cpu"] = {
                "current": cpu_values[-1] if cpu_values else 0,
                "forecast_next_3": cpu_forecast,
                "alert": any(v > 90 for v in cpu_forecast),
            }

        if ram_forecast:
            result["ram"] = {
                "current": ram_values[-1] if ram_values else 0,
                "forecast_next_3": ram_forecast,
                "alert": any(v > 90 for v in ram_forecast),
            }

        if disk_forecast:
            result["disk"] = {
                "current": disk_values[-1] if disk_values else 0,
                "forecast_next_3": disk_forecast,
                "alert": any(v > 90 for v in disk_forecast),
            }

        return result

    # ------------------------------------------------------------------
    # Scheduling Optimization
    # ------------------------------------------------------------------

    def suggest_optimal_time(self, task_type: str, duration_minutes: int = 30) -> str:
        """Suggest the best time to run a heavy task based on usage patterns."""
        if self.behavior_analyzer:
            peak_hours = self.behavior_analyzer.get_peak_hours()
            # Suggest off-peak hours
            all_hours = list(range(24))
            off_peak = [h for h in all_hours if h not in peak_hours]
            if off_peak:
                # Prefer business hours off-peak
                business_off_peak = [h for h in off_peak if 8 <= h <= 22]
                best = business_off_peak[0] if business_off_peak else off_peak[0]
                return f"Best time for '{task_type}': {best:02d}:00 (off-peak)"

        # Default: suggest early morning
        return f"Best time for '{task_type}': 06:00 (early morning, low activity expected)"

    # ------------------------------------------------------------------
    # Proactive Suggestions
    # ------------------------------------------------------------------

    def get_proactive_suggestions(self, system_status: Optional[Dict] = None) -> List[str]:
        """Generate proactive suggestions based on current state."""
        suggestions = []

        now = datetime.now()

        # Morning briefing
        if 7 <= now.hour <= 9:
            suggestions.append("Good morning! Would you like your daily briefing?")

        # End of work day
        if now.hour == 17 and now.weekday() < 5:
            suggestions.append("End of work day — shall I summarize today's activities?")

        # System health warnings
        if system_status:
            if system_status.get("cpu_percent", 0) > 80:
                suggestions.append("CPU usage is high — want me to check running processes?")
            if system_status.get("disk_percent", 0) > 85:
                suggestions.append("Disk is nearly full — want me to run a cleanup?")
            if system_status.get("ram_percent", 0) > 85:
                suggestions.append("RAM usage is high — want me to free up memory?")

        return suggestions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _simple_extrapolate(values: List[float], steps: int) -> List[float]:
        if not values:
            return []
        if len(values) == 1:
            return [values[0]] * steps
        delta = (values[-1] - values[0]) / max(len(values) - 1, 1)
        return [round(values[-1] + delta * (i + 1), 2) for i in range(steps)]

    def get_prediction_accuracy(self) -> float:
        """Placeholder: return prediction accuracy (requires feedback loop)."""
        return 0.0
