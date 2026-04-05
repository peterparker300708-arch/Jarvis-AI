"""
Theme Manager - UI theme management for Jarvis AI.
"""

import logging
from typing import Dict, List

from utils.config import Config

logger = logging.getLogger(__name__)

THEMES = {
    "dark": {
        "bg_primary": "#0a0e1a",
        "bg_secondary": "#111827",
        "bg_card": "#1e293b",
        "accent": "#00d4ff",
        "accent_2": "#7daaff",
        "text_primary": "#e2e8f0",
        "text_secondary": "#94a3b8",
    },
    "light": {
        "bg_primary": "#f8fafc",
        "bg_secondary": "#ffffff",
        "bg_card": "#f1f5f9",
        "accent": "#0ea5e9",
        "accent_2": "#6366f1",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
    },
    "iron-man": {
        "bg_primary": "#1a0a00",
        "bg_secondary": "#2d1500",
        "bg_card": "#3d2000",
        "accent": "#ff6b00",
        "accent_2": "#ffd700",
        "text_primary": "#ffe8cc",
        "text_secondary": "#c49a6c",
    },
    "matrix": {
        "bg_primary": "#000000",
        "bg_secondary": "#0a0a0a",
        "bg_card": "#001100",
        "accent": "#00ff00",
        "accent_2": "#00cc00",
        "text_primary": "#00ff00",
        "text_secondary": "#00aa00",
    },
}


class ThemeManager:
    def __init__(self, config: Config):
        self.config = config
        self._current = config.get("ui.default_theme", "dark")

    def set_theme(self, theme_name: str) -> bool:
        if theme_name in THEMES:
            self._current = theme_name
            logger.info(f"Theme changed to: {theme_name}")
            return True
        return False

    def get_theme(self) -> Dict:
        return THEMES.get(self._current, THEMES["dark"])

    def get_current_name(self) -> str:
        return self._current

    def list_themes(self) -> List[str]:
        return list(THEMES.keys())

    def get_css_vars(self) -> str:
        """Return CSS custom properties for the current theme."""
        theme = self.get_theme()
        lines = [":root {"]
        for k, v in theme.items():
            lines.append(f"  --{k.replace('_', '-')}: {v};")
        lines.append("}")
        return "\n".join(lines)
