"""
Screenshot & Screen Recorder Module for Jarvis AI.
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from utils.config import Config

logger = logging.getLogger(__name__)


class ScreenshotRecorder:
    """
    Capture screenshots and record screen activity.
    Uses Pillow for screenshots.
    """

    def __init__(self, config: Config):
        self.config = config
        self.output_dir = Path(config.get("paths.screenshots", "~/Pictures/Jarvis")).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._pillow_available = self._check_pillow()
        self._pyautogui_available = self._check_pyautogui()

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def take_screenshot(self, filename: Optional[str] = None, region: Optional[Tuple] = None) -> Optional[str]:
        """
        Capture a screenshot.
        region: (left, top, width, height) or None for full screen.
        Returns the saved file path or None on failure.
        """
        if not self._pillow_available:
            logger.warning("Pillow not available — cannot take screenshot")
            return None

        try:
            from PIL import ImageGrab
            if region:
                left, top, width, height = region
                bbox = (left, top, left + width, top + height)
                img = ImageGrab.grab(bbox=bbox)
            else:
                img = ImageGrab.grab()

            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"

            out_path = self.output_dir / filename
            img.save(str(out_path))
            logger.info(f"Screenshot saved: {out_path}")
            return str(out_path)
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None

    def take_timed_screenshots(self, count: int = 5, interval: float = 1.0) -> list:
        """Take multiple screenshots at regular intervals."""
        paths = []
        for i in range(count):
            path = self.take_screenshot()
            if path:
                paths.append(path)
            if i < count - 1:
                time.sleep(interval)
        return paths

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

    def ocr_screenshot(self, image_path: str) -> Optional[str]:
        """Extract text from a screenshot using OCR."""
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text.strip()
        except ImportError:
            logger.warning("pytesseract not available — OCR disabled")
            return None
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Organize
    # ------------------------------------------------------------------

    def list_screenshots(self) -> list:
        """Return all screenshots in the output directory."""
        return [
            {
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
            }
            for f in sorted(self.output_dir.glob("*.png"), key=lambda x: x.stat().st_ctime, reverse=True)
        ]

    def cleanup_old(self, days: int = 30) -> int:
        """Delete screenshots older than `days` days."""
        cutoff = time.time() - days * 86400
        deleted = 0
        for f in self.output_dir.glob("*.png"):
            if f.stat().st_ctime < cutoff:
                f.unlink()
                deleted += 1
        logger.info(f"Cleaned up {deleted} old screenshots")
        return deleted

    # ------------------------------------------------------------------

    @staticmethod
    def _check_pillow() -> bool:
        try:
            from PIL import ImageGrab  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_pyautogui() -> bool:
        try:
            import pyautogui  # noqa: F401
            return True
        except ImportError:
            return False
