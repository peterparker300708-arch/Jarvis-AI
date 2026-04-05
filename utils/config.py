"""Configuration loader with YAML support, defaults, and singleton access."""

from __future__ import annotations

import os
import threading
from typing import Any

_DEFAULTS: dict[str, Any] = {
    "app": {
        "name": "Jarvis AI",
        "version": "1.0.0",
        "debug": False,
        "log_level": "INFO",
    },
    "ai": {
        "provider": "ollama",
        "ollama_url": "http://localhost:11434",
        "model": "llama3",
        "temperature": 0.7,
        "max_tokens": 1024,
        "timeout": 30,
        "fallback_to_rules": True,
    },
    "voice": {
        "enabled": True,
        "wake_word": "jarvis",
        "tts_engine": "pyttsx3",
        "language": "en-US",
        "speech_rate": 175,
        "volume": 1.0,
    },
    "database": {
        "path": "data/jarvis.db",
        "echo": False,
    },
    "web": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False,
        "secret_key": "change-me-in-production",
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": False,
    },
    "scheduler": {
        "timezone": "UTC",
        "max_instances": 3,
        "coalesce": True,
    },
    "system": {
        "allow_shutdown": False,
        "allow_restart": False,
        "command_timeout": 30,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* without mutating either."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class _AttrDict(dict):
    """Dict subclass that supports attribute-style access."""

    def __getattr__(self, item: str) -> Any:
        try:
            value = self[item]
        except KeyError:
            raise AttributeError(f"Config has no setting '{item}'") from None
        if isinstance(value, dict):
            return _AttrDict(value)
        return value

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


class Config:
    """Singleton configuration object loaded from *config.yaml*.

    Usage::

        cfg = Config.get_instance()
        print(cfg.app.name)
        print(cfg.ai.model)
    """

    _instance: Config | None = None
    _lock = threading.Lock()

    def __new__(cls) -> "Config":
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._data = _AttrDict(_DEFAULTS)
                instance._load()
                cls._instance = instance
        return cls._instance

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "Config":
        """Return the singleton :class:`Config` instance."""
        return cls()

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton (mainly useful in tests)."""
        with cls._lock:
            cls._instance = None

    def get(self, key: str, default: Any = None) -> Any:
        """Dot-separated key lookup, e.g. ``cfg.get('ai.model')``.

        Args:
            key: Dot-separated path, e.g. ``"ai.model"``.
            default: Value returned when key is absent.
        """
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, key: str, value: Any) -> None:
        """Set a config value via dot-separated key."""
        parts = key.split(".")
        node: dict = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    def __getattr__(self, item: str) -> Any:
        try:
            value = self._data[item]
        except KeyError:
            raise AttributeError(f"Config has no section '{item}'") from None
        if isinstance(value, dict):
            return _AttrDict(value)
        return value

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Attempt to load config.yaml from the project root."""
        config_path = self._find_config_file()
        if config_path is None:
            return
        try:
            import yaml  # type: ignore[import]
            with open(config_path, "r", encoding="utf-8") as fh:
                user_cfg = yaml.safe_load(fh) or {}
            self._data = _AttrDict(_deep_merge(dict(self._data), user_cfg))
        except ImportError:
            # PyYAML not installed — fall back to defaults silently
            pass
        except Exception as exc:  # noqa: BLE001
            print(f"[Config] Warning: could not load config.yaml: {exc}")

    @staticmethod
    def _find_config_file() -> str | None:
        """Search upward from this file for config.yaml."""
        search_dirs = [
            os.getcwd(),
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ]
        for directory in search_dirs:
            candidate = os.path.join(directory, "config.yaml")
            if os.path.isfile(candidate):
                return candidate
        return None
