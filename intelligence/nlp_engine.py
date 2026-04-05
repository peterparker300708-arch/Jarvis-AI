"""
NLP Engine - Advanced Natural Language Processing for Jarvis AI.
Multi-language support, intent recognition, and entity extraction.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from utils.config import Config

logger = logging.getLogger(__name__)


class NLPEngine:
    """
    Handles:
    - Language detection
    - Auto-translation to English
    - Intent recognition
    - Named entity extraction
    - Text preprocessing
    """

    # Simple intent rules (keyword → intent)
    INTENT_PATTERNS = {
        "open_app": [r"\bopen\b", r"\blaunch\b", r"\bstart\b"],
        "close_app": [r"\bclose\b", r"\bkill\b", r"\bstop\b"],
        "search_web": [r"\bsearch\b", r"\bgoogle\b", r"\blook up\b", r"\bfind\b"],
        "system_status": [r"\bstatus\b", r"\bhealth\b", r"\bhow is\b", r"\bmonitor\b"],
        "schedule": [r"\bschedule\b", r"\bremind\b", r"\bmeeting\b", r"\bappointment\b"],
        "file_operation": [r"\bcreate\b", r"\bdelete\b", r"\bmove\b", r"\bcopy\b", r"\bfile\b", r"\bfolder\b"],
        "weather": [r"\bweather\b", r"\btemperature\b", r"\bforecast\b"],
        "email": [r"\bemail\b", r"\bmail\b", r"\bsend\b", r"\binbox\b"],
        "calculate": [r"\bcalculate\b", r"\bcompute\b", r"\bmath\b", r"\b\d+\s*[\+\-\*\/]\s*\d+"],
        "joke": [r"\bjoke\b", r"\bfunny\b", r"\blaugh\b"],
        "help": [r"\bhelp\b", r"\bcommands\b", r"\bwhat can you\b"],
        "exit": [r"\bexit\b", r"\bquit\b", r"\bbye\b", r"\bgoodbye\b"],
        "greeting": [r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgood morning\b", r"\bgood evening\b"],
        "time_query": [r"\btime\b", r"\bclock\b", r"\bwhat time\b"],
        "date_query": [r"\bdate\b", r"\bday\b", r"\btoday\b"],
        "analytics": [r"\breport\b", r"\banalyze\b", r"\bstatistics?\b", r"\binsight\b"],
        "automation": [r"\bautomate\b", r"\bworkflow\b", r"\btrigger\b", r"\broutine\b"],
    }

    def __init__(self, config: Config):
        self.config = config
        self._langdetect_available = False
        self._translator_available = False
        self._spacy_nlp = None
        self._init_optional_deps()

    def _init_optional_deps(self):
        """Lazily import optional NLP dependencies."""
        try:
            from langdetect import detect  # noqa: F401
            self._langdetect_available = True
        except ImportError:
            pass

        try:
            from deep_translator import GoogleTranslator  # noqa: F401
            self._translator_available = True
        except ImportError:
            pass

        try:
            import spacy
            try:
                self._spacy_nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy model loaded")
            except OSError:
                logger.debug("spaCy model 'en_core_web_sm' not found — basic NLP mode")
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Language Detection & Translation
    # ------------------------------------------------------------------

    def detect_language(self, text: str) -> str:
        """Detect the language of the text (ISO 639-1 code)."""
        if not self._langdetect_available:
            return "en"
        try:
            from langdetect import detect
            return detect(text)
        except Exception:
            return "en"

    def translate_to_english(self, text: str, source_lang: str = "auto") -> str:
        """Translate text to English."""
        lang = self.detect_language(text)
        if lang == "en":
            return text
        if not self._translator_available:
            logger.debug("Translation not available — returning original text")
            return text
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source=source_lang, target="en").translate(text)
            return translated or text
        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            return text

    # ------------------------------------------------------------------
    # Intent Recognition
    # ------------------------------------------------------------------

    def recognize_intent(self, text: str) -> Dict:
        """
        Recognize the primary intent from text.
        Returns: {intent, confidence, matched_patterns}
        """
        text_lower = text.lower()
        scores: Dict[str, int] = {}

        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, text_lower))
            if score > 0:
                scores[intent] = score

        if not scores:
            return {"intent": "general_chat", "confidence": 0.5, "matched_patterns": []}

        best_intent = max(scores, key=scores.get)  # type: ignore[arg-type]
        total_patterns = len(self.INTENT_PATTERNS.get(best_intent, []))
        confidence = min(scores[best_intent] / max(total_patterns, 1), 1.0)

        return {
            "intent": best_intent,
            "confidence": round(confidence, 2),
            "matched_patterns": list(scores.keys()),
        }

    # ------------------------------------------------------------------
    # Entity Extraction
    # ------------------------------------------------------------------

    def extract_entities(self, text: str) -> List[Dict]:
        """
        Extract named entities from text.
        Returns list of {text, label, start, end}.
        """
        if self._spacy_nlp:
            return self._extract_with_spacy(text)
        return self._extract_with_regex(text)

    def _extract_with_spacy(self, text: str) -> List[Dict]:
        doc = self._spacy_nlp(text)
        return [
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
            for ent in doc.ents
        ]

    def _extract_with_regex(self, text: str) -> List[Dict]:
        """Lightweight regex-based entity extraction."""
        entities = []

        # Time patterns (e.g., "3 PM", "14:30")
        for m in re.finditer(r"\b(\d{1,2}:\d{2}(?:\s*[AP]M)?|\d{1,2}\s*[AP]M)\b", text, re.IGNORECASE):
            entities.append({"text": m.group(), "label": "TIME", "start": m.start(), "end": m.end()})

        # Date patterns
        for m in re.finditer(
            r"\b(today|tomorrow|yesterday|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|"
            r"January|February|March|April|May|June|July|August|September|October|November|December)\b",
            text,
            re.IGNORECASE,
        ):
            entities.append({"text": m.group(), "label": "DATE", "start": m.start(), "end": m.end()})

        # URL patterns
        for m in re.finditer(r"https?://[^\s]+", text):
            entities.append({"text": m.group(), "label": "URL", "start": m.start(), "end": m.end()})

        # Email
        for m in re.finditer(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", text, re.IGNORECASE):
            entities.append({"text": m.group(), "label": "EMAIL", "start": m.start(), "end": m.end()})

        # Numbers
        for m in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
            entities.append({"text": m.group(), "label": "NUMBER", "start": m.start(), "end": m.end()})

        return entities

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    def preprocess(self, text: str) -> str:
        """Clean and normalize text."""
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def tokenize(self, text: str) -> List[str]:
        """Simple whitespace tokenizer."""
        if self._spacy_nlp:
            return [t.text for t in self._spacy_nlp(text)]
        return text.lower().split()

    def get_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """Extract the most important keywords (stop-word filtered)."""
        STOP_WORDS = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "to", "of", "in", "on", "at",
            "for", "with", "by", "from", "up", "about", "into", "through",
            "i", "you", "he", "she", "it", "we", "they", "and", "or", "but",
            "not", "no", "my", "your", "his", "her", "its", "our", "their",
        }
        tokens = re.findall(r"\b[a-z]{3,}\b", text.lower())
        filtered = [t for t in tokens if t not in STOP_WORDS]
        from collections import Counter
        return [word for word, _ in Counter(filtered).most_common(top_n)]

    def analyze(self, text: str) -> Dict:
        """Full NLP analysis pipeline."""
        preprocessed = self.preprocess(text)
        translated = self.translate_to_english(preprocessed)
        intent = self.recognize_intent(translated)
        entities = self.extract_entities(translated)
        keywords = self.get_keywords(translated)

        return {
            "original": text,
            "preprocessed": preprocessed,
            "translated": translated,
            "language": self.detect_language(text),
            "intent": intent,
            "entities": entities,
            "keywords": keywords,
        }
