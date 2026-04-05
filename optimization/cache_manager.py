"""
Cache Manager - Smart caching system for Jarvis AI.
"""

import hashlib
import json
import logging
import time
from typing import Any, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class CacheManager:
    """
    In-memory and disk-backed cache with TTL expiration.
    """

    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.get("optimization.cache_enabled", True)
        self.default_ttl = config.get("optimization.cache_ttl", 3600)
        self._cache: dict = {}  # {key: {"value": ..., "expires": float}}
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache. Returns None if missing or expired."""
        if not self.enabled:
            return None
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        if time.time() > entry["expires"]:
            del self._cache[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store a value in cache with optional TTL."""
        if not self.enabled:
            return
        self._cache[key] = {
            "value": value,
            "expires": time.time() + (ttl if ttl is not None else self.default_ttl),
            "created": time.time(),
        }

    def delete(self, key: str) -> bool:
        """Remove a key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    def purge_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        now = time.time()
        expired_keys = [k for k, v in self._cache.items() if now > v["expires"]]
        for k in expired_keys:
            del self._cache[k]
        return len(expired_keys)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def make_key(*args) -> str:
        """Create a deterministic cache key from arguments."""
        raw = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get_stats(self) -> dict:
        """Return cache statistics."""
        self.purge_expired()
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(self._hits + self._misses, 1), 3),
            "enabled": self.enabled,
        }

    def cached(self, ttl: Optional[int] = None):
        """
        Decorator factory for caching function return values.
        Usage: @cache.cached(ttl=300)
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                key = self.make_key(func.__qualname__, args, kwargs)
                cached_val = self.get(key)
                if cached_val is not None:
                    return cached_val
                result = func(*args, **kwargs)
                self.set(key, result, ttl)
                return result
            wrapper.__wrapped__ = func
            return wrapper
        return decorator
