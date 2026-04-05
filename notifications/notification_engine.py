"""
Notification Engine - Multi-channel notifications for Jarvis AI.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class NotificationEngine:
    """
    Send notifications via:
    - Desktop (plyer)
    - Console
    - Telegram Bot
    - Email (SMTP)
    """

    def __init__(self, config: Config):
        self.config = config
        self._plyer_available = self._check_plyer()
        self._history: List[Dict] = []

    # ------------------------------------------------------------------
    # Main Interface
    # ------------------------------------------------------------------

    def notify(
        self,
        title: str,
        message: str,
        priority: str = "normal",
        channel: str = "auto",
        icon: Optional[str] = None,
    ) -> bool:
        """
        Send a notification.
        channel: auto | desktop | console | telegram | email
        priority: low | normal | high | critical
        """
        entry = {
            "title": title,
            "message": message,
            "priority": priority,
            "channel": channel,
            "timestamp": datetime.now().isoformat(),
            "sent": False,
        }

        if channel == "console" or (channel == "auto" and not self._plyer_available):
            self._notify_console(title, message, priority)
            entry["sent"] = True
            entry["channel"] = "console"
        elif channel == "desktop" or (channel == "auto" and self._plyer_available):
            sent = self._notify_desktop(title, message)
            if not sent:
                self._notify_console(title, message, priority)
            entry["sent"] = True
            entry["channel"] = "desktop"
        elif channel == "telegram":
            entry["sent"] = self._notify_telegram(title, message)
        elif channel == "email":
            entry["sent"] = self._notify_email(title, message)

        self._history.append(entry)
        return entry["sent"]

    # ------------------------------------------------------------------
    # Channels
    # ------------------------------------------------------------------

    def _notify_console(self, title: str, message: str, priority: str = "normal"):
        ICONS = {"low": "ℹ️", "normal": "🔔", "high": "⚠️", "critical": "🚨"}
        icon = ICONS.get(priority, "🔔")
        print(f"\n{icon} [{title}] {message}\n")

    def _notify_desktop(self, title: str, message: str) -> bool:
        if not self._plyer_available:
            return False
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="Jarvis AI",
                timeout=5,
            )
            return True
        except Exception as e:
            logger.debug(f"Desktop notification failed: {e}")
            return False

    def _notify_telegram(self, title: str, message: str) -> bool:
        token = self.config.get("notifications.telegram_bot_token")
        chat_id = self.config.get("notifications.telegram_chat_id")
        if not token or not chat_id:
            logger.warning("Telegram credentials not configured")
            return False
        try:
            import requests
            text = f"*{title}*\n{message}"
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
            return resp.ok
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    def _notify_email(self, subject: str, body: str) -> bool:
        smtp_host = self.config.get("notifications.smtp_host")
        smtp_user = self.config.get("notifications.smtp_user")
        smtp_pass = self.config.get("notifications.smtp_password")
        if not smtp_host or not smtp_user:
            logger.warning("Email SMTP not configured")
            return False
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = f"[Jarvis AI] {subject}"
            msg["From"] = smtp_user
            msg["To"] = smtp_user
            with smtplib.SMTP(smtp_host, self.config.get("notifications.smtp_port", 587)) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 50) -> List[Dict]:
        return list(reversed(self._history[-limit:]))

    @staticmethod
    def _check_plyer() -> bool:
        try:
            from plyer import notification  # noqa: F401
            return True
        except ImportError:
            return False
