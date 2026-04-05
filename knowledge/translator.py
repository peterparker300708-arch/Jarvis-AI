"""
Translator - Real-time multi-language translation for Jarvis AI.
"""

import logging
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "af": "Afrikaans", "ar": "Arabic", "bg": "Bulgarian", "bn": "Bengali",
    "ca": "Catalan", "cs": "Czech", "cy": "Welsh", "da": "Danish",
    "de": "German", "el": "Greek", "en": "English", "es": "Spanish",
    "et": "Estonian", "fa": "Persian", "fi": "Finnish", "fr": "French",
    "gu": "Gujarati", "he": "Hebrew", "hi": "Hindi", "hr": "Croatian",
    "hu": "Hungarian", "id": "Indonesian", "it": "Italian", "ja": "Japanese",
    "kn": "Kannada", "ko": "Korean", "lt": "Lithuanian", "lv": "Latvian",
    "mk": "Macedonian", "ml": "Malayalam", "mr": "Marathi", "ms": "Malay",
    "mt": "Maltese", "nl": "Dutch", "no": "Norwegian", "pl": "Polish",
    "pt": "Portuguese", "ro": "Romanian", "ru": "Russian", "sk": "Slovak",
    "sl": "Slovenian", "sq": "Albanian", "sr": "Serbian", "sv": "Swedish",
    "sw": "Swahili", "ta": "Tamil", "te": "Telugu", "th": "Thai",
    "tl": "Filipino", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu",
    "vi": "Vietnamese", "zh-CN": "Chinese (Simplified)", "zh-TW": "Chinese (Traditional)",
}


class Translator:
    """
    Multi-language translation using deep-translator (Google Translate backend).
    Gracefully degrades to no-op when the library is unavailable.
    """

    def __init__(self, config: Config):
        self.config = config
        self._available = self._check_available()
        self._langdetect_available = self._check_langdetect()
        self._translation_memory: Dict[str, str] = {}

    # ------------------------------------------------------------------

    def translate(self, text: str, target: str = "en", source: str = "auto") -> Dict:
        """
        Translate text to the target language.
        Returns: {original, translated, source_lang, target_lang, from_cache}
        """
        if not text.strip():
            return self._result(text, text, source, target)

        cache_key = f"{source}:{target}:{text}"
        if cache_key in self._translation_memory:
            r = self._result(text, self._translation_memory[cache_key], source, target)
            r["from_cache"] = True
            return r

        if not self._available:
            return self._result(text, text, source, target, error="Translation library unavailable")

        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source=source, target=target).translate(text)
            self._translation_memory[cache_key] = translated
            return self._result(text, translated or text, source, target)
        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            return self._result(text, text, source, target, error=str(e))

    def detect_language(self, text: str) -> str:
        """Detect the language of a text."""
        if not self._langdetect_available:
            return "en"
        try:
            from langdetect import detect
            return detect(text)
        except Exception:
            return "en"

    def translate_batch(self, texts: List[str], target: str = "en") -> List[Dict]:
        """Translate a list of texts."""
        return [self.translate(t, target=target) for t in texts]

    def get_supported_languages(self) -> Dict[str, str]:
        return SUPPORTED_LANGUAGES

    def get_language_name(self, code: str) -> str:
        return SUPPORTED_LANGUAGES.get(code, code)

    # ------------------------------------------------------------------

    def _result(
        self,
        original: str,
        translated: str,
        source: str,
        target: str,
        error: Optional[str] = None,
    ) -> Dict:
        return {
            "original": original,
            "translated": translated,
            "source_lang": source,
            "target_lang": target,
            "success": error is None,
            "error": error,
            "from_cache": False,
        }

    @staticmethod
    def _check_available() -> bool:
        try:
            from deep_translator import GoogleTranslator  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_langdetect() -> bool:
        try:
            from langdetect import detect  # noqa: F401
            return True
        except ImportError:
            return False
