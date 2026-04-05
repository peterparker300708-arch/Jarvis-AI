"""Voice engine: speech recognition and text-to-speech with graceful fallbacks."""

from __future__ import annotations

import io
import queue
import threading
import time
from typing import Callable, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency guards
# ---------------------------------------------------------------------------

try:
    import speech_recognition as sr  # type: ignore[import]
    _SR_AVAILABLE = True
except ImportError:
    sr = None  # type: ignore[assignment]
    _SR_AVAILABLE = False
    logger.warning("speech_recognition not installed — voice input disabled.")

try:
    import pyttsx3  # type: ignore[import]
    _PYTTSX3_AVAILABLE = True
except ImportError:
    pyttsx3 = None  # type: ignore[assignment]
    _PYTTSX3_AVAILABLE = False

try:
    from gtts import gTTS  # type: ignore[import]
    _GTTS_AVAILABLE = True
except ImportError:
    gTTS = None  # type: ignore[assignment]
    _GTTS_AVAILABLE = False

if not _PYTTSX3_AVAILABLE and not _GTTS_AVAILABLE:
    logger.warning("Neither pyttsx3 nor gTTS installed — TTS output disabled.")


# ---------------------------------------------------------------------------
# Voice engine
# ---------------------------------------------------------------------------

class VoiceEngine:
    """Unified voice I/O engine.

    Provides:
    * :meth:`listen` – capture microphone audio and return recognized text.
    * :meth:`speak` – synthesize and play text via pyttsx3 or gTTS.
    * :meth:`start_listening_daemon` – background thread that watches for the
      wake word and invokes a callback.
    * :meth:`stop_listening_daemon` – gracefully stop the daemon thread.

    All heavy objects (recognizer, TTS engine) are lazily instantiated so the
    class is safe to import even when optional packages are absent.

    Args:
        wake_word: Wake word that activates Jarvis (case-insensitive).
        language: BCP-47 language tag for speech recognition.
        tts_engine: Preferred TTS backend — ``"pyttsx3"`` or ``"gtts"``.
        speech_rate: Words-per-minute rate for pyttsx3 (default 175).
        volume: pyttsx3 volume 0.0–1.0 (default 1.0).
        on_wake: Optional callback invoked with transcribed text after wake word.
    """

    def __init__(
        self,
        wake_word: str = "jarvis",
        language: str = "en-US",
        tts_engine: str = "pyttsx3",
        speech_rate: int = 175,
        volume: float = 1.0,
        on_wake: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.wake_word = wake_word.lower()
        self.language = language
        self.tts_engine_name = tts_engine
        self.speech_rate = speech_rate
        self.volume = volume
        self.on_wake = on_wake

        self._recognizer: Optional[object] = None
        self._microphone: Optional[object] = None
        self._tts_engine: Optional[object] = None
        self._tts_lock = threading.Lock()

        # Daemon state
        self._daemon_thread: Optional[threading.Thread] = None
        self._daemon_stop_event = threading.Event()
        self._speech_queue: queue.Queue[str] = queue.Queue()

    # ------------------------------------------------------------------
    # Speech recognition
    # ------------------------------------------------------------------

    def listen(
        self,
        timeout: int = 5,
        phrase_time_limit: int = 10,
    ) -> Optional[str]:
        """Listen for speech via the microphone and return the transcription.

        Args:
            timeout: Seconds to wait for the user to start speaking.
            phrase_time_limit: Maximum seconds to capture a single phrase.

        Returns:
            Recognized text string, or ``None`` on failure.
        """
        if not _SR_AVAILABLE:
            logger.error("speech_recognition is not installed.")
            return None

        recognizer = self._get_recognizer()
        mic = self._get_microphone()
        if mic is None:
            return None

        try:
            with mic as source:  # type: ignore[attr-defined]
                recognizer.adjust_for_ambient_noise(source, duration=0.3)  # type: ignore[attr-defined]
                logger.debug("Listening…")
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)  # type: ignore[attr-defined]

            text = recognizer.recognize_google(audio, language=self.language)  # type: ignore[attr-defined]
            logger.info("Recognized: %r", text)
            return text
        except sr.WaitTimeoutError:  # type: ignore[union-attr]
            logger.debug("No speech detected within timeout.")
            return None
        except sr.UnknownValueError:  # type: ignore[union-attr]
            logger.debug("Speech unintelligible.")
            return None
        except sr.RequestError as exc:  # type: ignore[union-attr]
            logger.warning("Google STT API error: %s", exc)
            return None
        except OSError as exc:
            logger.error("Microphone error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Text-to-speech
    # ------------------------------------------------------------------

    def speak(self, text: str) -> bool:
        """Synthesize *text* and play it through the system speakers.

        Tries pyttsx3 first, then gTTS, then logs the text to stdout as a
        last resort.

        Args:
            text: String to speak aloud.

        Returns:
            ``True`` if audio was successfully produced.
        """
        if not text:
            return False

        logger.info("TTS: %r", text)

        if self.tts_engine_name == "pyttsx3" and _PYTTSX3_AVAILABLE:
            return self._speak_pyttsx3(text)
        if _GTTS_AVAILABLE:
            return self._speak_gtts(text)
        if _PYTTSX3_AVAILABLE:
            return self._speak_pyttsx3(text)

        # Final fallback: just print
        print(f"[Jarvis]: {text}")
        return True

    def _speak_pyttsx3(self, text: str) -> bool:
        with self._tts_lock:
            try:
                engine = self._get_tts_engine()
                if engine is None:
                    return False
                engine.say(text)  # type: ignore[attr-defined]
                engine.runAndWait()  # type: ignore[attr-defined]
                return True
            except Exception as exc:  # noqa: BLE001
                logger.error("pyttsx3 error: %s", exc)
                # Re-initialize on error
                self._tts_engine = None
                return False

    def _speak_gtts(self, text: str) -> bool:
        try:
            tts = gTTS(text=text, lang=self.language.split("-")[0])  # type: ignore[call-arg]
            buf = io.BytesIO()
            tts.write_to_fp(buf)  # type: ignore[attr-defined]
            buf.seek(0)
            self._play_audio_bytes(buf.read())
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("gTTS error: %s", exc)
            return False

    @staticmethod
    def _play_audio_bytes(data: bytes) -> None:
        """Play raw MP3 bytes via pygame or write to a temp file and play."""
        try:
            import pygame  # type: ignore[import]
            pygame.mixer.init()
            buf = io.BytesIO(data)
            pygame.mixer.music.load(buf)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.quit()
            return
        except ImportError:
            pass

        # Fallback: write to file and play with system command
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(data)
            tmp_path = f.name
        from utils.helpers import get_platform, run_command
        p = get_platform()
        if p == "linux":
            run_command(f"mpg123 -q {tmp_path} 2>/dev/null || afplay {tmp_path} 2>/dev/null")
        elif p == "mac":
            run_command(f"afplay {tmp_path}")
        elif p == "windows":
            run_command(f'start /min wmplayer "{tmp_path}"')
        import os
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Wake word detection
    # ------------------------------------------------------------------

    def is_wake_word(self, text: str) -> bool:
        """Return ``True`` if *text* contains the configured wake word.

        Args:
            text: Transcribed speech string.

        Returns:
            ``True`` when the wake word appears in *text*.
        """
        return self.wake_word in text.lower()

    # ------------------------------------------------------------------
    # Background daemon
    # ------------------------------------------------------------------

    def start_listening_daemon(
        self,
        callback: Optional[Callable[[str], None]] = None,
        poll_interval: float = 0.1,
    ) -> bool:
        """Start a background thread that continuously listens for the wake word.

        When the wake word is detected the callback (or :attr:`on_wake`) is
        invoked in the daemon thread with the full transcribed text.

        Args:
            callback: Function called with transcribed text after wake word.
            poll_interval: Seconds to sleep between recognition attempts.

        Returns:
            ``True`` if the daemon was started, ``False`` if already running
            or if speech recognition is unavailable.
        """
        if not _SR_AVAILABLE:
            logger.error("Cannot start voice daemon: speech_recognition not installed.")
            return False
        if self._daemon_thread and self._daemon_thread.is_alive():
            logger.warning("Voice daemon already running.")
            return False

        effective_callback = callback or self.on_wake
        self._daemon_stop_event.clear()
        self._daemon_thread = threading.Thread(
            target=self._daemon_loop,
            args=(effective_callback, poll_interval),
            daemon=True,
            name="VoiceDaemon",
        )
        self._daemon_thread.start()
        logger.info("Voice listening daemon started (wake word: %r).", self.wake_word)
        return True

    def stop_listening_daemon(self, join_timeout: float = 5.0) -> None:
        """Signal the background daemon to stop and optionally join.

        Args:
            join_timeout: Seconds to wait for the thread to finish.
        """
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_stop_event.set()
            self._daemon_thread.join(timeout=join_timeout)
            logger.info("Voice daemon stopped.")
        self._daemon_thread = None

    def is_daemon_running(self) -> bool:
        """Return ``True`` if the background listener thread is alive."""
        return self._daemon_thread is not None and self._daemon_thread.is_alive()

    def _daemon_loop(
        self,
        callback: Optional[Callable[[str], None]],
        poll_interval: float,
    ) -> None:
        """Internal loop executed in the daemon thread."""
        logger.debug("Voice daemon loop started.")
        while not self._daemon_stop_event.is_set():
            try:
                text = self.listen(timeout=3, phrase_time_limit=8)
                if text and self.is_wake_word(text):
                    logger.info("Wake word detected in: %r", text)
                    if callback:
                        try:
                            callback(text)
                        except Exception as exc:  # noqa: BLE001
                            logger.error("Wake callback raised: %s", exc)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Daemon loop exception: %s", exc)
            time.sleep(poll_interval)
        logger.debug("Voice daemon loop exited.")

    # ------------------------------------------------------------------
    # Lazy resource constructors
    # ------------------------------------------------------------------

    def _get_recognizer(self):
        if self._recognizer is None and _SR_AVAILABLE:
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
        return self._recognizer

    def _get_microphone(self):
        if not _SR_AVAILABLE:
            return None
        if self._microphone is None:
            try:
                self._microphone = sr.Microphone()
            except OSError as exc:
                logger.error("No microphone available: %s", exc)
                return None
        return self._microphone

    def _get_tts_engine(self):
        if not _PYTTSX3_AVAILABLE:
            return None
        if self._tts_engine is None:
            try:
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty("rate", self.speech_rate)
                self._tts_engine.setProperty("volume", self.volume)
            except Exception as exc:  # noqa: BLE001
                logger.error("Could not initialize pyttsx3: %s", exc)
                return None
        return self._tts_engine
