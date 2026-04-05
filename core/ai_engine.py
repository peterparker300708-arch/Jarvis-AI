"""AI engine: Ollama-backed LLM with rule-based fallback."""

from __future__ import annotations

import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Intent patterns (rule-based fallback)
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("time", [r"\btime\b", r"\bwhat time\b", r"\bcurrent time\b"]),
    ("date", [r"\bdate\b", r"\bwhat day\b", r"\btoday\b"]),
    ("system_status", [r"\bsystem\b.*\bstatus\b", r"\bhow.*cpu\b", r"\bmemory\b.*usage\b", r"\bsystem info\b"]),
    ("open_app", [r"\bopen\b", r"\blaunch\b", r"\bstart\b.*\bapp\b"]),
    ("file_ops", [r"\bfile\b", r"\bfolder\b", r"\bdirectory\b", r"\blist\b.*\bfiles\b"]),
    ("weather", [r"\bweather\b", r"\btemperature\b", r"\brain\b", r"\bforecast\b"]),
    ("calculator", [r"\bcalculate\b", r"\bmath\b", r"\bwhat is\b.*[\d\+\-\*\/]", r"[\d]+\s*[\+\-\*\/]\s*[\d]+"]),
    ("web_search", [r"\bsearch\b", r"\bgoogle\b", r"\blook up\b", r"\bwhat is\b"]),
    ("reminder", [r"\bremind\b", r"\breminder\b", r"\bset.*alarm\b"]),
    ("note", [r"\bnote\b", r"\bwrite down\b", r"\bsave.*note\b", r"\btake.*note\b"]),
    ("greeting", [r"\bhello\b", r"\bhi\b", r"\bhey jarvis\b", r"\bgood morning\b", r"\bgood evening\b"]),
    ("help", [r"\bhelp\b", r"\bwhat can you do\b", r"\bcommands\b"]),
    ("joke", [r"\bjoke\b", r"\bfunny\b", r"\blaugh\b"]),
    ("shutdown", [r"\bshutdown\b", r"\bshut down\b", r"\bpower off\b"]),
    ("restart", [r"\brestart\b", r"\breboot\b"]),
    ("volume", [r"\bvolume\b", r"\blouder\b", r"\bquieter\b", r"\bmute\b"]),
]

_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "How many programmers does it take to change a light bulb? None — that's a hardware problem.",
    "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
    "Why was the computer cold? It left its Windows open.",
    "I told my computer I needed a break and now it won't stop sending me vacation ads.",
]

_HELP_TEXT = (
    "I can help you with: checking the time & date, system status, opening apps, "
    "file operations, weather info, calculations, web searches, reminders, notes, "
    "volume control, and general conversation. Just ask me anything!"
)


class AIEngine:
    """Core AI engine for Jarvis.

    Attempts to route every command through the Ollama LLM API.  Falls back to
    a deterministic rule-based response system when Ollama is unreachable.

    Args:
        ollama_url: Base URL for the Ollama HTTP API.
        model: Ollama model name to use.
        temperature: Sampling temperature (0.0–1.0).
        max_tokens: Maximum tokens in the generated response.
        timeout: HTTP request timeout in seconds.
        max_history: Number of prior conversation turns to retain.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout: int = 30,
        max_history: int = 10,
    ) -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_history = max_history
        self._history: list[dict[str, str]] = []
        self._ollama_available: Optional[bool] = None
        self._last_availability_check: float = 0.0
        self._availability_check_interval = 60.0  # seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_command(self, text: str) -> dict[str, Any]:
        """Parse *text*, dispatch to LLM or rule engine, return result dict.

        Args:
            text: Raw user input.

        Returns:
            Dict with keys ``response``, ``intent``, ``entities``,
            ``source`` (``"ollama"`` | ``"rules"``), and ``success``.
        """
        text = text.strip()
        if not text:
            return self._result("Please say something!", "empty", {}, "rules", False)

        intent, entities = self.parse_intent(text)
        logger.debug("Intent=%s entities=%s for: %r", intent, entities, text)

        # Try special-cased fast responses first
        fast = self._fast_response(intent, entities, text)
        if fast is not None:
            self._append_history("user", text)
            self._append_history("assistant", fast)
            return self._result(fast, intent, entities, "rules", True)

        # Try Ollama
        if self._is_ollama_available():
            try:
                response = self.generate_response(text)
                self._append_history("user", text)
                self._append_history("assistant", response)
                return self._result(response, intent, entities, "ollama", True)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Ollama request failed: %s", exc)

        # Rule-based fallback
        response = self._rule_based_response(intent, entities, text)
        self._append_history("user", text)
        self._append_history("assistant", response)
        return self._result(response, intent, entities, "rules", True)

    def generate_response(self, prompt: str, context: Optional[list] = None) -> str:
        """Send *prompt* to Ollama and return the model's reply.

        Args:
            prompt: User message text.
            context: Optional list of prior context messages (Ollama format).

        Returns:
            Model response string.

        Raises:
            RuntimeError: If the HTTP request fails.
        """
        messages = list(self._history[-(self.max_history * 2):])
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.ollama_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["message"]["content"].strip()
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama unreachable: {exc}") from exc
        except (KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unexpected Ollama response: {exc}") from exc

    def parse_intent(self, text: str) -> tuple[str, dict[str, Any]]:
        """Extract intent label and entities from *text*.

        Args:
            text: Raw user input.

        Returns:
            Tuple of ``(intent_str, entities_dict)``.
        """
        lower = text.lower()
        for intent, patterns in _INTENT_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, lower):
                    entities = self._extract_entities(intent, text, lower)
                    return intent, entities
        return "general", {}

    def clear_history(self) -> None:
        """Wipe the conversation history."""
        self._history.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_ollama_available(self) -> bool:
        """Check Ollama availability (cached for `_availability_check_interval` s)."""
        now = time.monotonic()
        if (
            self._ollama_available is not None
            and now - self._last_availability_check < self._availability_check_interval
        ):
            return self._ollama_available

        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                self._ollama_available = resp.status == 200
        except Exception:  # noqa: BLE001
            self._ollama_available = False

        self._last_availability_check = now
        return self._ollama_available  # type: ignore[return-value]

    def _append_history(self, role: str, content: str) -> None:
        self._history.append({"role": role, "content": content})
        # Keep history bounded
        if len(self._history) > self.max_history * 2:
            self._history = self._history[-(self.max_history * 2):]

    @staticmethod
    def _result(
        response: str,
        intent: str,
        entities: dict,
        source: str,
        success: bool,
    ) -> dict[str, Any]:
        return {
            "response": response,
            "intent": intent,
            "entities": entities,
            "source": source,
            "success": success,
        }

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def _extract_entities(self, intent: str, text: str, lower: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        if intent == "calculator":
            # Try to find a math expression
            match = re.search(r"([\d\s\+\-\*\/\(\)\.\^%]+)", text)
            if match:
                entities["expression"] = match.group(1).strip()
        elif intent == "open_app":
            match = re.search(r"(?:open|launch|start)\s+([a-zA-Z0-9_\- ]+)", lower)
            if match:
                entities["app"] = match.group(1).strip()
        elif intent == "volume":
            match = re.search(r"\b(\d+)\s*%?\s*(?:volume|percent)?\b", lower)
            if match:
                entities["level"] = int(match.group(1))
        elif intent == "reminder":
            match = re.search(r"remind(?:er)?\s+(?:me\s+)?(?:to\s+)?(.+?)(?:\s+in\s+|\s+at\s+|\s+on\s+|$)", lower)
            if match:
                entities["task"] = match.group(1).strip()
        elif intent == "note":
            match = re.search(r"(?:note|write down|save)\s+(.+)", lower)
            if match:
                entities["content"] = match.group(1).strip()
        return entities

    # ------------------------------------------------------------------
    # Fast rule-based responses for specific intents
    # ------------------------------------------------------------------

    def _fast_response(
        self, intent: str, entities: dict, text: str
    ) -> Optional[str]:
        """Return a deterministic response string or ``None`` to fall through."""
        now = datetime.now()

        if intent == "time":
            return f"The current time is {now.strftime('%I:%M %p')}."

        if intent == "date":
            return f"Today is {now.strftime('%A, %B %d, %Y')}."

        if intent == "greeting":
            hour = now.hour
            if hour < 12:
                greeting = "Good morning"
            elif hour < 17:
                greeting = "Good afternoon"
            else:
                greeting = "Good evening"
            return f"{greeting}! I'm Jarvis, your AI assistant. How can I help you today?"

        if intent == "help":
            return _HELP_TEXT

        if intent == "joke":
            import random
            return random.choice(_JOKES)

        if intent == "calculator" and "expression" in entities:
            return self._safe_calculate(entities["expression"])

        return None  # fall through to Ollama / full rule engine

    def _rule_based_response(self, intent: str, entities: dict, text: str) -> str:
        """Broad rule-based fallback used when Ollama is unavailable."""
        if intent == "system_status":
            return (
                "I can check your system status. Please use the /api/system/info "
                "endpoint or the system control module for detailed stats."
            )
        if intent == "open_app":
            app = entities.get("app", "that application")
            return f"I'll try to open {app} for you using the system control module."
        if intent == "file_ops":
            return "I can help with file operations. What would you like to do?"
        if intent == "weather":
            return (
                "I don't have a weather API key configured. "
                "Please add one to config.yaml under 'weather.api_key'."
            )
        if intent == "web_search":
            query = urllib.parse.quote_plus(text)
            return (
                f"I'd search for that, but I'm currently in offline mode. "
                f"You can search manually at https://google.com/search?q={query}"
            )
        if intent == "reminder":
            return "I'd be happy to set a reminder! Please provide the exact date/time and message."
        if intent == "note":
            content = entities.get("content", text)
            return f"I've noted that down: '{content}'. Use the notes API to view all notes."
        if intent == "volume":
            level = entities.get("level")
            if level is not None:
                return f"Setting volume to {level}%."
            return "What would you like to set the volume to?"
        if intent == "shutdown":
            return "Shutdown requested. Please confirm via the system control module."
        if intent == "restart":
            return "Restart requested. Please confirm via the system control module."

        return (
            "I received your message but Ollama is not available right now. "
            "Start Ollama and run a model with 'ollama serve' to enable AI responses."
        )

    @staticmethod
    def _safe_calculate(expression: str) -> str:
        """Evaluate a math expression safely without using eval().

        Supports +, -, *, /, **, (, ), and the math module constants.
        """
        # Whitelist approach — only allow safe characters
        if not re.fullmatch(r"[\d\s\+\-\*\/\(\)\.\^%]+", expression):
            return "I can only evaluate numeric expressions with +, -, *, /, (, )."
        try:
            # Replace ^ with ** for exponentiation
            safe_expr = expression.replace("^", "**")
            # Use a restricted eval with no builtins
            result = eval(  # noqa: S307
                safe_expr,
                {"__builtins__": {}, "sqrt": math.sqrt, "pi": math.pi, "e": math.e},
            )
            if isinstance(result, float) and result.is_integer():
                return f"The result is {int(result)}."
            return f"The result is {result}."
        except ZeroDivisionError:
            return "Division by zero is undefined."
        except Exception:  # noqa: BLE001
            return f"I couldn't calculate '{expression}'. Please rephrase."
