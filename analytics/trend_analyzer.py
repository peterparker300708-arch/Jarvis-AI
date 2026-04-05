"""
Trend Analyzer - Identify patterns and trends in data.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from utils.config import Config

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Identifies trends, seasonality, and anomalies in time series data.
    """

    def __init__(self, config: Config):
        self.config = config

    def analyze_trend(self, values: List[float]) -> Dict:
        """
        Analyze the trend direction of a list of numeric values.
        Returns: {direction, strength, average, min, max, range}
        """
        if not values:
            return {"direction": "unknown", "strength": 0}

        if len(values) == 1:
            return {
                "direction": "stable",
                "strength": 0,
                "average": values[0],
                "min": values[0],
                "max": values[0],
                "range": 0,
            }

        # Simple linear regression
        n = len(values)
        x = list(range(n))
        mean_x = sum(x) / n
        mean_y = sum(values) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, values))
        denominator = sum((xi - mean_x) ** 2 for xi in x)
        slope = numerator / denominator if denominator != 0 else 0

        # Normalize slope to a -1..1 range
        value_range = max(values) - min(values)
        if value_range > 0:
            strength = min(abs(slope * n) / value_range, 1.0)
        else:
            strength = 0.0

        direction = "increasing" if slope > 0.01 else ("decreasing" if slope < -0.01 else "stable")

        return {
            "direction": direction,
            "slope": round(slope, 4),
            "strength": round(strength, 3),
            "average": round(mean_y, 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "range": round(max(values) - min(values), 3),
            "samples": n,
        }

    def detect_anomalies(self, values: List[float], z_threshold: float = 2.0) -> List[Tuple[int, float]]:
        """
        Detect anomalies using z-score method.
        Returns list of (index, value) tuples where anomalies were found.
        """
        if len(values) < 3:
            return []
        try:
            import statistics
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            if stdev == 0:
                return []
            return [(i, v) for i, v in enumerate(values) if abs(v - mean) / stdev > z_threshold]
        except Exception:
            return []

    def moving_average(self, values: List[float], window: int = 5) -> List[float]:
        """Compute a simple moving average."""
        if not values or window < 1:
            return []
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            result.append(round(sum(values[start : i + 1]) / (i - start + 1), 4))
        return result

    def seasonal_decompose(self, values: List[float], period: int = 7) -> Dict:
        """
        Very simple seasonal decomposition: extract trend + residual.
        """
        if len(values) < period * 2:
            return {"trend": values, "seasonal": [0] * len(values), "residual": [0] * len(values)}

        trend = self.moving_average(values, period)
        seasonal_avg = []
        for i in range(len(values)):
            seasonal_avg.append(values[i] - trend[i] if trend[i] else 0)

        residual = [values[i] - trend[i] - seasonal_avg[i] for i in range(len(values))]
        return {
            "trend": [round(v, 4) for v in trend],
            "seasonal": [round(v, 4) for v in seasonal_avg],
            "residual": [round(v, 4) for v in residual],
        }

    def forecast_simple(self, values: List[float], steps: int = 7) -> List[float]:
        """Simple linear extrapolation forecast."""
        trend = self.analyze_trend(values)
        slope = trend.get("slope", 0)
        last = values[-1] if values else 0
        return [round(last + slope * (i + 1), 4) for i in range(steps)]

    def compare_periods(self, period_a: List[float], period_b: List[float]) -> Dict:
        """Compare two time periods."""
        if not period_a or not period_b:
            return {}
        import statistics
        mean_a = statistics.mean(period_a)
        mean_b = statistics.mean(period_b)
        change = round((mean_b - mean_a) / mean_a * 100, 2) if mean_a != 0 else 0
        return {
            "period_a_mean": round(mean_a, 3),
            "period_b_mean": round(mean_b, 3),
            "change_percent": change,
            "direction": "increase" if change > 0 else "decrease" if change < 0 else "no change",
        }
