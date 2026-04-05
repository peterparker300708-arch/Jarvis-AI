"""
AI Engine - Core intelligence layer for Jarvis AI.
Handles communication with the LLM backend (Ollama, OpenAI, etc.)
and orchestrates high-level AI reasoning.
"""

import logging
import json
import time
from typing import Optional, Generator

import requests

from utils.config import Config

logger = logging.getLogger(__name__)


class AIEngine:
    """Primary AI reasoning engine backed by an LLM provider."""

    SYSTEM_PROMPT = (
        "You are Jarvis, an advanced AI assistant. "
        "You are helpful, precise, and proactive. "
        "You have full awareness of the user's system, schedule, and preferences. "
        "Respond concisely unless asked for detailed explanations."
    )

    def __init__(self, config: Config, memory=None, context=None):
        self.config = config
        self.memory = memory
        self.context = context
        self.provider = config.get("ai.provider", "ollama")
        self.model = config.get("ai.model", "mistral")
        self.base_url = config.get("ai.base_url", "http://localhost:11434")
        self.temperature = config.get("ai.temperature", 0.7)
        self.max_tokens = config.get("ai.max_tokens", 2048)
        self.timeout = config.get("ai.timeout", 30)
        self._available = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chat(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        """Send a message and return the assistant response."""
        messages = self._build_messages(user_input, system_prompt)
        try:
            if self.provider == "ollama":
                return self._ollama_chat(messages)
            else:
                return self._fallback_response(user_input)
        except Exception as e:
            logger.error(f"AI engine error: {e}")
            return f"I encountered an error: {e}. Please check the AI backend connection."

    def stream_chat(self, user_input: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        """Stream a response token-by-token (generator)."""
        messages = self._build_messages(user_input, system_prompt)
        if self.provider == "ollama":
            yield from self._ollama_stream(messages)
        else:
            yield self._fallback_response(user_input)

    def is_available(self) -> bool:
        """Check whether the AI backend is reachable."""
        if self._available is not None:
            return self._available
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            self._available = resp.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def list_models(self) -> list:
        """Return available models from the Ollama backend."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception as e:
            logger.warning(f"Could not list models: {e}")
            return []

    def analyze_intent(self, text: str) -> dict:
        """
        Analyze user intent and return a structured dict:
        {intent, entities, confidence, action}
        """
        prompt = (
            "Analyze the following user input and respond ONLY with valid JSON "
            "containing keys: intent (string), entities (list of strings), "
            "confidence (float 0-1), action (string, one of: "
            "system_control|web_search|calendar|file_ops|chat|analytics|automation|unknown).\n\n"
            f"Input: {text}"
        )
        try:
            raw = self.chat(prompt, system_prompt="You are an NLU classifier. Respond only in JSON.")
            return json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Intent analysis fallback: {e}")
            return {"intent": text, "entities": [], "confidence": 0.5, "action": "unknown"}

    def summarize(self, text: str, max_words: int = 100) -> str:
        """Summarize a piece of text."""
        prompt = f"Summarize the following in at most {max_words} words:\n\n{text}"
        return self.chat(prompt)

    def generate_code(self, description: str, language: str = "python") -> str:
        """Generate code from a natural language description."""
        prompt = (
            f"Write {language} code for the following requirement. "
            "Return only the code block, no explanations:\n\n"
            f"{description}"
        )
        return self.chat(prompt)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(self, user_input: str, system_prompt: Optional[str]) -> list:
        """Build the messages list, optionally including conversation history."""
        system = system_prompt or self.SYSTEM_PROMPT
        messages = [{"role": "system", "content": system}]

        # Inject recent conversation history
        if self.memory:
            try:
                history = self.memory.get_recent(limit=6)
                for entry in history:
                    messages.append({"role": entry["role"], "content": entry["content"]})
            except Exception:
                pass

        messages.append({"role": "user", "content": user_input})
        return messages

    def _ollama_chat(self, messages: list) -> str:
        """Call the Ollama /api/chat endpoint."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()

    def _ollama_stream(self, messages: list) -> Generator[str, None, None]:
        """Stream from the Ollama /api/chat endpoint."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": self.temperature},
        }
        with requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            stream=True,
            timeout=self.timeout,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue

    def _fallback_response(self, user_input: str) -> str:
        """Simple rule-based fallback when the AI backend is unavailable."""
        lowered = user_input.lower()
        if any(w in lowered for w in ("hello", "hi", "hey")):
            return "Hello! I'm Jarvis. How can I assist you today?"
        if "time" in lowered:
            return f"The current time is {time.strftime('%H:%M:%S')}."
        if "date" in lowered:
            return f"Today is {time.strftime('%A, %B %d, %Y')}."
        return (
            "I'm currently operating in offline mode — the AI backend is unavailable. "
            "Please start Ollama and try again."
        )
