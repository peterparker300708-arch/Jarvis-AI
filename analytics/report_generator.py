"""
Report Generator - Create HTML and text reports for Jarvis AI.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional

from utils.config import Config

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #0a0e1a; color: #e0e0e0; margin: 0; padding: 20px; }}
  h1 {{ color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px; }}
  h2 {{ color: #7daaff; margin-top: 30px; }}
  .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 20px; margin: 15px 0; }}
  .metric {{ display: inline-block; background: #1e293b; border-radius: 6px; padding: 10px 20px; margin: 5px; text-align: center; }}
  .metric .value {{ font-size: 2em; color: #00d4ff; font-weight: bold; }}
  .metric .label {{ font-size: 0.8em; color: #94a3b8; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
  th {{ background: #1e293b; color: #7daaff; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #1f2937; }}
  tr:hover td {{ background: #1e293b; }}
  .badge {{ background: #1d4ed8; color: #fff; border-radius: 12px; padding: 2px 10px; font-size: 0.8em; }}
  footer {{ margin-top: 40px; color: #475569; font-size: 0.8em; text-align: center; }}
</style>
</head>
<body>
<h1>🤖 {title}</h1>
<p>Generated: {generated_at}</p>
{content}
<footer>Jarvis AI - Advanced Edition v2.0.0</footer>
</body>
</html>
"""


class ReportGenerator:
    """Generate formatted HTML and JSON reports."""

    def __init__(self, config: Config):
        self.config = config
        self.reports_dir = config.get("analytics.reports_dir", "reports")
        os.makedirs(self.reports_dir, exist_ok=True)

    # ------------------------------------------------------------------

    def generate_system_report(self, system_status: Dict, performance_history: list) -> str:
        """Generate an HTML system health report."""
        cpu = system_status.get("cpu_percent", 0)
        ram = system_status.get("ram_percent", 0)
        disk = system_status.get("disk_percent", 0)

        def _color(val):
            if val > 90:
                return "#ef4444"
            elif val > 75:
                return "#f59e0b"
            return "#10b981"

        metrics_html = f"""
<div class="card">
  <h2>System Health</h2>
  <div class="metric">
    <div class="value" style="color:{_color(cpu)}">{cpu}%</div>
    <div class="label">CPU Usage</div>
  </div>
  <div class="metric">
    <div class="value" style="color:{_color(ram)}">{ram}%</div>
    <div class="label">RAM Usage</div>
  </div>
  <div class="metric">
    <div class="value" style="color:{_color(disk)}">{disk}%</div>
    <div class="label">Disk Usage</div>
  </div>
  <div class="metric">
    <div class="value">{system_status.get('ram_total_gb', 0)} GB</div>
    <div class="label">Total RAM</div>
  </div>
  <div class="metric">
    <div class="value">{system_status.get('disk_total_gb', 0)} GB</div>
    <div class="label">Total Disk</div>
  </div>
</div>
"""

        content = metrics_html
        return self._save_html("System Health Report", content, "system_report")

    def generate_activity_report(self, behavior_profile: Dict, daily_summary: Dict) -> str:
        """Generate an activity report."""
        top_cats = behavior_profile.get("top_categories", [])
        rows = "".join(
            f"<tr><td>{c['category']}</td><td>{c['count']}</td></tr>"
            for c in top_cats
        )
        table = f"""
<div class="card">
  <h2>Top Command Categories</h2>
  <table><tr><th>Category</th><th>Count</th></tr>{rows}</table>
</div>
<div class="card">
  <h2>Today's Summary</h2>
  <div class="metric">
    <div class="value">{daily_summary.get('total_events', 0)}</div>
    <div class="label">Total Events</div>
  </div>
  <div class="metric">
    <div class="value">{behavior_profile.get('total_commands', 0)}</div>
    <div class="label">Commands</div>
  </div>
  <div class="metric">
    <div class="value">{round(behavior_profile.get('success_rate', 0) * 100)}%</div>
    <div class="label">Success Rate</div>
  </div>
</div>
"""
        return self._save_html("Activity Report", table, "activity_report")

    def generate_custom_report(self, title: str, data: Dict) -> str:
        """Generate a custom JSON + HTML report."""
        rows = ""
        for key, value in data.items():
            rows += f"<tr><td>{key}</td><td>{value}</td></tr>"
        content = f"""
<div class="card">
  <h2>Data</h2>
  <table><tr><th>Key</th><th>Value</th></tr>{rows}</table>
</div>
"""
        return self._save_html(title, content, "custom_report")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _save_html(self, title: str, content: str, prefix: str) -> str:
        filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(self.reports_dir, filename)
        html = HTML_TEMPLATE.format(
            title=title,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            content=content,
        )
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"Report saved: {filepath}")
        return filepath

    def list_reports(self):
        """List all saved reports."""
        reports = []
        for f in sorted(os.listdir(self.reports_dir)):
            fp = os.path.join(self.reports_dir, f)
            if os.path.isfile(fp):
                reports.append({"name": f, "path": fp, "size": os.path.getsize(fp)})
        return reports
