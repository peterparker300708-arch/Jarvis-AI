"""
Voice Engine - Speech recognition and text-to-speech for Jarvis AI.
"""

import logging
import threading
import time
from typing import Optional, Callable

from utils.config import Config

logger = logging.getLogger(__name__)


class VoiceEngine:
    """
    Manages speech recognition (STT) and text-to-speech (TTS).
    Gracefully degrades when audio libraries are unavailable.
    """

    PERSONALITIES = {
        "jarvis": {"rate": 180, "volume": 1.0, "voice_gender": "male"},
        "friday": {"rate": 190, "volume": 0.95, "voice_gender": "female"},
        "edith": {"rate": 200, "volume": 0.9, "voice_gender": "female"},
        "custom": {"rate": 175, "volume": 1.0, "voice_gender": "male"},
    }

    def __init__(self, config: Config, ai_engine=None):
        self.config = config
        self.ai_engine = ai_engine
        self._tts_engine = None
        self._recognizer = None
        self._microphone = None
        self._listening = False
        self._wake_word = config.get("voice.wake_word", "jarvis").lower()
        self._personality = config.get("voice.personality", "jarvis")
        self._on_command_callback: Optional[Callable[[str], None]] = None
        self._tts_available = False
        self._stt_available = False
        self._init_tts()
        self._init_stt()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _init_tts(self):
        """Initialize the TTS engine."""
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            props = self.PERSONALITIES.get(self._personality, self.PERSONALITIES["jarvis"])
            self._tts_engine.setProperty("rate", self.config.get("voice.rate", props["rate"]))
            self._tts_engine.setProperty("volume", self.config.get("voice.volume", props["volume"]))
            voices = self._tts_engine.getProperty("voices")
            if voices:
                preferred_gender = props["voice_gender"]
                for voice in voices:
                    name = voice.name.lower()
                    if preferred_gender == "male" and any(w in name for w in ("male", "david", "mark", "james")):
                        self._tts_engine.setProperty("voice", voice.id)
                        break
                    elif preferred_gender == "female" and any(w in name for w in ("female", "zira", "hazel", "karen")):
                        self._tts_engine.setProperty("voice", voice.id)
                        break
            self._tts_available = True
            logger.info("TTS engine initialized (pyttsx3)")
        except ImportError:
            logger.warning("pyttsx3 not available — TTS disabled")
        except Exception as e:
            logger.warning(f"TTS init failed: {e}")

    def _init_stt(self):
        """Initialize the speech recognition engine."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._microphone = sr.Microphone()
            # Adjust for ambient noise briefly
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self._stt_available = True
            logger.info("STT engine initialized (SpeechRecognition)")
        except ImportError:
            logger.warning("SpeechRecognition not available — STT disabled")
        except Exception as e:
            logger.warning(f"STT init failed: {e}")

    # ------------------------------------------------------------------
    # Text-to-Speech
    # ------------------------------------------------------------------

    def speak(self, text: str, block: bool = False):
        """Convert text to speech."""
        logger.debug(f"Speaking: {text[:80]}...")
        if self._tts_available and self._tts_engine:
            if block:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
            else:
                t = threading.Thread(target=self._speak_async, args=(text,), daemon=True)
                t.start()
        else:
            print(f"[JARVIS]: {text}")

    def _speak_async(self, text: str):
        try:
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
        except Exception as e:
            logger.warning(f"TTS speak error: {e}")

    # ------------------------------------------------------------------
    # Speech Recognition
    # ------------------------------------------------------------------

    def listen(self, timeout: int = 5) -> Optional[str]:
        """Listen for a single voice command and return the text."""
        if not self._stt_available:
            logger.warning("STT not available")
            return None
        try:
            import speech_recognition as sr
            with self._microphone as source:
                logger.debug("Listening...")
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            engine = self.config.get("voice.recognition_engine", "google")
            if engine == "sphinx":
                return self._recognizer.recognize_sphinx(audio)
            else:
                return self._recognizer.recognize_google(audio, language=self.config.get("voice.language", "en-US"))
        except Exception as e:
            logger.debug(f"Listen error: {e}")
            return None

    def start_listening(self, callback: Optional[Callable[[str], None]] = None):
        """Start continuous wake-word listening loop."""
        self._listening = True
        self._on_command_callback = callback
        logger.info(f"Voice listening started (wake word: '{self._wake_word}')")
        self.speak(f"Jarvis online. Listening for '{self._wake_word}'.")
        while self._listening:
            try:
                text = self.listen(timeout=3)
                if text and self._wake_word in text.lower():
                    self.speak("Yes?")
                    command = self.listen(timeout=8)
                    if command:
                        logger.info(f"Voice command: {command}")
                        if callback:
                            callback(command)
                        elif self.ai_engine:
                            response = self.ai_engine.chat(command)
                            self.speak(response)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.debug(f"Listening loop error: {e}")
                time.sleep(0.5)

    def stop_listening(self):
        """Stop the continuous listening loop."""
        self._listening = False
        logger.info("Voice listening stopped")

    # ------------------------------------------------------------------
    # Personality
    # ------------------------------------------------------------------

    def set_personality(self, name: str):
        """Switch voice personality."""
        if name in self.PERSONALITIES:
            self._personality = name
            props = self.PERSONALITIES[name]
            if self._tts_engine:
                self._tts_engine.setProperty("rate", props["rate"])
                self._tts_engine.setProperty("volume", props["volume"])
            logger.info(f"Voice personality changed to: {name}")
        else:
            logger.warning(f"Unknown personality: {name}")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        return {
            "tts_available": self._tts_available,
            "stt_available": self._stt_available,
            "listening": self._listening,
            "wake_word": self._wake_word,
            "personality": self._personality,
        }
