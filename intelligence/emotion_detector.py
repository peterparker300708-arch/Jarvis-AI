"""
Emotion Detector - Analyze tone and emotional state from text/voice.
"""

import logging
import re
from typing import Dict, List, Tuple

from utils.config import Config

logger = logging.getLogger(__name__)


class EmotionDetector:
    """
    Detect emotional state from text input and adapt response tone.
    Uses lexicon-based approach with optional ML enhancement.
    """

    EMOTION_LEXICON = {
        "happy": [
            "happy", "joy", "excited", "great", "awesome", "fantastic", "wonderful",
            "amazing", "love", "thrilled", "delighted", "glad", "pleased", "brilliant",
            "excellent", "superb", "perfect", ":)", ":-)", "😊", "😄", "🎉",
        ],
        "frustrated": [
            "frustrated", "annoyed", "angry", "upset", "irritated", "mad", "furious",
            "hate", "terrible", "awful", "horrible", "stupid", "broken", "ugh", "damn",
            "not working", "doesn't work", "why won't", "stop it", "😠", "😡",
        ],
        "sad": [
            "sad", "depressed", "unhappy", "miserable", "lonely", "crying", "disappointed",
            "heartbroken", "hopeless", "terrible day", "awful", ":(", ":-(", "😢", "😞",
        ],
        "stressed": [
            "stressed", "anxious", "overwhelmed", "pressure", "deadline", "panic",
            "worried", "nervous", "tense", "urgent", "critical", "asap", "help me",
        ],
        "neutral": [
            "okay", "fine", "alright", "sure", "yes", "no", "maybe", "ok",
        ],
        "curious": [
            "curious", "wonder", "interesting", "fascinating", "how", "why", "what",
            "tell me", "explain", "describe", "?",
        ],
        "confident": [
            "confident", "sure", "certain", "definitely", "absolutely", "of course",
            "clearly", "obviously", "precisely",
        ],
    }

    RESPONSE_TONE_MAP = {
        "happy": "enthusiastic",
        "frustrated": "calm_and_empathetic",
        "sad": "empathetic_and_supportive",
        "stressed": "focused_and_reassuring",
        "neutral": "professional",
        "curious": "informative",
        "confident": "collaborative",
    }

    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.get("emotion.enabled", True)
        self.sensitivity = config.get("emotion.sensitivity", 0.7)
        self._vader_available = self._check_vader()

    # ------------------------------------------------------------------

    def detect(self, text: str) -> Dict:
        """
        Detect emotions in text.
        Returns: {emotions, dominant, confidence, response_tone, sentiment_score}
        """
        if not self.enabled:
            return self._neutral_result()

        scores = self._lexicon_scores(text)

        # Enhance with VADER if available
        if self._vader_available:
            scores = self._enhance_with_vader(text, scores)

        if not scores:
            return self._neutral_result()

        total = sum(scores.values())
        normalized = {e: round(s / total, 3) for e, s in scores.items()} if total else {}
        dominant = max(scores, key=scores.get)  # type: ignore[arg-type]
        confidence = round(normalized.get(dominant, 0), 3)

        return {
            "emotions": normalized,
            "dominant": dominant,
            "confidence": confidence,
            "response_tone": self.RESPONSE_TONE_MAP.get(dominant, "professional"),
            "adapt_response": self.config.get("emotion.adapt_responses", True),
            "stress_level": self._stress_level(scores),
        }

    def _neutral_result(self) -> Dict:
        return {
            "emotions": {"neutral": 1.0},
            "dominant": "neutral",
            "confidence": 1.0,
            "response_tone": "professional",
            "adapt_response": False,
            "stress_level": "low",
        }

    def _lexicon_scores(self, text: str) -> Dict[str, float]:
        text_lower = text.lower()
        scores: Dict[str, float] = {}
        for emotion, keywords in self.EMOTION_LEXICON.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                scores[emotion] = float(count)
        return scores

    def _enhance_with_vader(self, text: str, base_scores: Dict[str, float]) -> Dict[str, float]:
        """Use VADER sentiment to refine scores."""
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            sia = SentimentIntensityAnalyzer()
            polarity = sia.polarity_scores(text)
            compound = polarity["compound"]
            if compound >= 0.3:
                base_scores["happy"] = base_scores.get("happy", 0) + abs(compound)
            elif compound <= -0.3:
                base_scores["frustrated"] = base_scores.get("frustrated", 0) + abs(compound)
        except Exception:
            pass
        return base_scores

    def _stress_level(self, scores: Dict[str, float]) -> str:
        stress_emotions = scores.get("stressed", 0) + scores.get("frustrated", 0) + scores.get("sad", 0)
        if stress_emotions >= 3:
            return "high"
        elif stress_emotions >= 1:
            return "medium"
        return "low"

    def adapt_response(self, response: str, emotion_result: Dict) -> str:
        """Optionally prepend an empathetic opener based on detected emotion."""
        if not emotion_result.get("adapt_response", False):
            return response
        dominant = emotion_result.get("dominant", "neutral")
        openers = {
            "frustrated": "I understand this can be frustrating. ",
            "sad": "I'm sorry to hear that. ",
            "stressed": "Let me help you sort this out quickly. ",
            "happy": "Great to hear you're in a good mood! ",
            "curious": "Great question! ",
        }
        opener = openers.get(dominant, "")
        return opener + response

    @staticmethod
    def _check_vader() -> bool:
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer  # noqa: F401
            return True
        except ImportError:
            return False
