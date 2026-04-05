"""
Memory System - Conversation memory with persistence for Jarvis AI.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class MemorySystem:
    """
    Manages short-term and long-term conversation memory.
    - Short-term: last N turns in memory
    - Long-term: database-backed persistent storage
    - Smart recall: semantic search over history
    """

    def __init__(self, config: Config, db=None):
        self.config = config
        self.db = db
        self.max_turns = config.get("memory.max_turns", 50)
        self.persistence_enabled = config.get("memory.persistence", True)
        self._short_term: List[Dict] = []
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ------------------------------------------------------------------
    # Short-Term Memory
    # ------------------------------------------------------------------

    def add(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to short-term memory."""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "session_id": self._session_id,
            "metadata": metadata or {},
        }
        self._short_term.append(entry)

        # Trim to max_turns
        if len(self._short_term) > self.max_turns:
            self._short_term = self._short_term[-self.max_turns :]

        # Persist to DB
        if self.persistence_enabled and self.db:
            try:
                self.db.save_memory_entry(entry)
            except Exception as e:
                logger.debug(f"Memory persistence error: {e}")

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Return the most recent N conversation turns."""
        return list(reversed(self._short_term[-limit:])) if self._short_term else []

    def clear_short_term(self):
        """Clear short-term memory (start a new conversation context)."""
        self._short_term.clear()
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info("Short-term memory cleared")

    # ------------------------------------------------------------------
    # Long-Term Memory
    # ------------------------------------------------------------------

    def search_history(self, query: str, limit: int = 5) -> List[Dict]:
        """Simple keyword search over conversation history."""
        if self.db:
            try:
                return self.db.search_memory(query, limit)
            except Exception:
                pass
        # Fallback: search in-memory
        query_lower = query.lower()
        results = [
            e for e in self._short_term if query_lower in e["content"].lower()
        ]
        return results[-limit:]

    def get_context_window(self) -> List[Dict]:
        """Return the current conversation context window."""
        window_size = min(self.max_turns, len(self._short_term))
        return self._short_term[-window_size:]

    def summarize_session(self) -> str:
        """Generate a brief summary of the current session."""
        if not self._short_term:
            return "No conversation history in this session."

        turns = len(self._short_term)
        user_msgs = [e for e in self._short_term if e["role"] == "user"]
        keywords = set()
        for msg in user_msgs[-5:]:
            words = msg["content"].lower().split()
            keywords.update(w for w in words if len(w) > 4)

        return (
            f"Session {self._session_id}: {turns} messages, "
            f"topics: {', '.join(list(keywords)[:5]) or 'general conversation'}"
        )

    def get_all_sessions(self, limit: int = 20) -> List[Dict]:
        """Return recent sessions from the database."""
        if self.db:
            try:
                return self.db.get_memory_sessions(limit)
            except Exception:
                pass
        return []

    def recall(self, what: str) -> Optional[str]:
        """
        Try to recall something from memory.
        Example: "What was I researching last Tuesday?"
        """
        results = self.search_history(what, limit=3)
        if not results:
            return None
        return "\n".join(
            f"[{r.get('timestamp', 'unknown')}] {r['role']}: {r['content']}"
            for r in results
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Return memory statistics."""
        return {
            "short_term_count": len(self._short_term),
            "session_id": self._session_id,
            "max_turns": self.max_turns,
            "persistence_enabled": self.persistence_enabled,
        }
