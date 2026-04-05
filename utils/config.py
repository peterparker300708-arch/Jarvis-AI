"""
Configuration management for Jarvis AI.
"""

import os
import yaml
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Config:
    """Load and manage YAML configuration with dot-notation access."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.debug = False
        self._data: dict = {}
        self._load()

    def _load(self):
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
            self._data = {}
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
            logger.debug(f"Configuration loaded from {self.config_path}")
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse config file: {e}")
            self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot-notation.

        Example:
            config.get("web.port", 5000)
        """
        parts = key.split(".")
        value = self._data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        """Set a configuration value using dot-notation."""
        parts = key.split(".")
        data = self._data
        for part in parts[:-1]:
            data = data.setdefault(part, {})
        data[parts[-1]] = value

    def save(self):
        """Save current configuration back to file."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    def reload(self):
        """Reload configuration from file."""
        self._load()

    def to_dict(self) -> dict:
        """Return full configuration as a dictionary."""
        return dict(self._data)

    def __repr__(self) -> str:
        return f"Config(path={self.config_path!r})"
