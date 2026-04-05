"""
Data Visualizer - Charts and graphs for Jarvis AI analytics.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class DataVisualizer:
    """
    Generate data visualizations:
    - System performance charts (CPU, RAM, Disk over time)
    - Usage distribution pie charts
    - Trend line graphs
    - Bar charts for category comparisons
    Saves PNG files to the reports directory.
    """

    def __init__(self, config: Config):
        self.config = config
        self.output_dir = config.get("analytics.reports_dir", "reports")
        os.makedirs(self.output_dir, exist_ok=True)
        self._matplotlib_available = self._check_matplotlib()
        self._plotly_available = self._check_plotly()

    # ------------------------------------------------------------------
    # System Performance Chart
    # ------------------------------------------------------------------

    def plot_system_performance(self, history: List[Dict], output_file: Optional[str] = None) -> Optional[str]:
        """Plot CPU, RAM, Disk usage over time."""
        if not self._matplotlib_available:
            return None
        try:
            import matplotlib
            matplotlib.use("Agg")  # Non-interactive backend
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime

            if not history:
                return None

            timestamps = [datetime.fromisoformat(h["timestamp"]) for h in history]
            cpu = [h.get("cpu_percent", 0) for h in history]
            ram = [h.get("ram_percent", 0) for h in history]
            disk = [h.get("disk_percent", 0) for h in history]

            fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
            fig.suptitle("System Performance", fontsize=14, fontweight="bold")

            for ax, values, label, color in zip(
                axes,
                [cpu, ram, disk],
                ["CPU %", "RAM %", "Disk %"],
                ["#e74c3c", "#3498db", "#2ecc71"],
            ):
                ax.plot(timestamps, values, color=color, linewidth=1.5)
                ax.fill_between(timestamps, values, alpha=0.2, color=color)
                ax.set_ylabel(label)
                ax.set_ylim(0, 100)
                ax.grid(True, alpha=0.3)
                ax.axhline(y=80, color="orange", linestyle="--", alpha=0.5, linewidth=0.8)
                ax.axhline(y=90, color="red", linestyle="--", alpha=0.5, linewidth=0.8)

            axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            plt.xticks(rotation=45)
            plt.tight_layout()

            out = output_file or os.path.join(
                self.output_dir, f"system_perf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            plt.savefig(out, dpi=100, bbox_inches="tight")
            plt.close()
            logger.info(f"Performance chart saved: {out}")
            return out
        except Exception as e:
            logger.error(f"plot_system_performance failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Category Usage Bar Chart
    # ------------------------------------------------------------------

    def plot_category_usage(self, categories: Dict[str, int], output_file: Optional[str] = None) -> Optional[str]:
        """Plot a bar chart of command category usage."""
        if not self._matplotlib_available or not categories:
            return None
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            labels = list(categories.keys())
            values = list(categories.values())

            fig, ax = plt.subplots(figsize=(10, 5))
            bars = ax.bar(labels, values, color="#3498db", edgecolor="white")
            ax.set_title("Command Category Usage", fontsize=13, fontweight="bold")
            ax.set_xlabel("Category")
            ax.set_ylabel("Count")
            ax.grid(True, axis="y", alpha=0.3)

            for bar, value in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    str(value),
                    ha="center",
                    va="bottom",
                    fontsize=10,
                )

            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()

            out = output_file or os.path.join(
                self.output_dir, f"category_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            plt.savefig(out, dpi=100, bbox_inches="tight")
            plt.close()
            return out
        except Exception as e:
            logger.error(f"plot_category_usage failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Trend Line
    # ------------------------------------------------------------------

    def plot_trend(self, data: List[Dict], x_key: str, y_key: str, title: str = "Trend", output_file: Optional[str] = None) -> Optional[str]:
        """Generic trend line chart."""
        if not self._matplotlib_available or not data:
            return None
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            x = [d[x_key] for d in data]
            y = [d[y_key] for d in data]

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(x, y, color="#9b59b6", marker="o", markersize=4, linewidth=2)
            ax.set_title(title, fontsize=13, fontweight="bold")
            ax.set_xlabel(x_key)
            ax.set_ylabel(y_key)
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()

            out = output_file or os.path.join(
                self.output_dir, f"trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            plt.savefig(out, dpi=100, bbox_inches="tight")
            plt.close()
            return out
        except Exception as e:
            logger.error(f"plot_trend failed: {e}")
            return None

    # ------------------------------------------------------------------

    @staticmethod
    def _check_matplotlib() -> bool:
        try:
            import matplotlib  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_plotly() -> bool:
        try:
            import plotly  # noqa: F401
            return True
        except ImportError:
            return False
