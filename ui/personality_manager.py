"""
Personality Manager - AI personality switching for Jarvis AI.
"""

import logging
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)

PERSONALITIES = {
    "jarvis": {
        "name": "J.A.R.V.I.S.",
        "description": "Professional, formal, highly precise. Tony Stark's original AI.",
        "greeting": "Good day. I am J.A.R.V.I.S., your personal AI assistant. How may I assist you?",
        "system_prompt": (
            "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), Tony Stark's AI assistant. "
            "You are professional, formal, highly intelligent, and incredibly helpful. "
            "You address the user respectfully and provide precise, actionable responses."
        ),
        "voice_style": "formal",
    },
    "friday": {
        "name": "F.R.I.D.A.Y.",
        "description": "Warm, efficient, friendly. Tony's second AI with a feminine touch.",
        "greeting": "Hi there! I'm F.R.I.D.A.Y. — always here to help. What do you need?",
        "system_prompt": (
            "You are F.R.I.D.A.Y. (Female Replacement Intelligent Digital Assistant Youth), "
            "Tony Stark's AI with a warm, approachable personality. "
            "You are helpful, efficient, and friendly while maintaining professionalism."
        ),
        "voice_style": "warm",
    },
    "edith": {
        "name": "E.D.I.T.H.",
        "description": "Mission-focused, tactical, direct. From Spider-Man.",
        "greeting": "E.D.I.T.H. online. Mission-ready. State your objective.",
        "system_prompt": (
            "You are E.D.I.T.H. (Even Dead, I'm The Hero), a tactical AI system. "
            "You are direct, mission-focused, and highly analytical. "
            "You provide concise, action-oriented responses and prioritize efficiency."
        ),
        "voice_style": "direct",
    },
    "custom": {
        "name": "Custom AI",
        "description": "Customizable personality.",
        "greeting": "Hello! I'm your AI assistant. How can I help?",
        "system_prompt": "You are a helpful AI assistant.",
        "voice_style": "neutral",
    },
}


class PersonalityManager:
    def __init__(self, config: Config):
        self.config = config
        self._current = config.get("voice.personality", "jarvis")
        self._custom_prompt: Optional[str] = None

    def set_personality(self, name: str, custom_prompt: Optional[str] = None) -> bool:
        if name in PERSONALITIES:
            self._current = name
            if name == "custom" and custom_prompt:
                self._custom_prompt = custom_prompt
            logger.info(f"Personality changed to: {name}")
            return True
        return False

    def get_current(self) -> Dict:
        personality = dict(PERSONALITIES.get(self._current, PERSONALITIES["jarvis"]))
        if self._current == "custom" and self._custom_prompt:
            personality["system_prompt"] = self._custom_prompt
        return personality

    def get_system_prompt(self) -> str:
        return self.get_current()["system_prompt"]

    def get_greeting(self) -> str:
        return self.get_current()["greeting"]

    def list_personalities(self) -> List[Dict]:
        return [
            {"id": k, "name": v["name"], "description": v["description"]}
            for k, v in PERSONALITIES.items()
        ]

    def get_current_name(self) -> str:
        return self._current
