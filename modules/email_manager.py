"""Email manager supporting SMTP send and IMAP fetch with graceful no-config handling."""

from __future__ import annotations

import email as email_lib
import email.header
import imaplib
import smtplib
import ssl
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

_NOT_CONFIGURED = {
    "status": "error",
    "message": (
        "Email is not configured. Please provide smtp_host, smtp_port, "
        "username, and password when creating EmailManager."
    ),
}


class EmailManager:
    """SMTP + IMAP email manager.

    Args:
        smtp_host: SMTP server hostname (e.g. "smtp.gmail.com").
        smtp_port: SMTP port (587 for TLS, 465 for SSL).
        username: Email username / address.
        password: Email password or app-specific password.
        imap_host: IMAP server hostname (e.g. "imap.gmail.com").
        use_tls: Use STARTTLS (port 587). If False, uses SSL (port 465).
    """

    def __init__(
        self,
        smtp_host: str = "",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        imap_host: str = "",
        use_tls: bool = True,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.imap_host = imap_host or smtp_host.replace("smtp.", "imap.")
        self.use_tls = use_tls
        self._configured = bool(smtp_host and username and password)

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        html_body: Optional[str] = None,
    ) -> Dict[str, str]:
        """Send an email via SMTP.

        Args:
            to: Recipient address(es), comma-separated string or single address.
            subject: Email subject line.
            body: Plain-text body.
            attachments: Optional list of file paths to attach.
            html_body: Optional HTML alternative body.

        Returns:
            dict with: status ("success"/"error"), message.
        """
        if not self._configured:
            return _NOT_CONFIGURED

        msg = MIMEMultipart("alternative") if html_body else MIMEMultipart()
        msg["From"] = self.username
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        if attachments:
            for path in attachments:
                file_path = Path(path)
                if not file_path.exists():
                    logger.warning("Attachment not found: %s", path)
                    continue
                part = MIMEBase("application", "octet-stream")
                with file_path.open("rb") as fh:
                    part.set_payload(fh.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
                msg.attach(part)

        recipients = [r.strip() for r in to.split(",")]
        try:
            if self.use_tls:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.login(self.username, self.password)
                    server.sendmail(self.username, recipients, msg.as_string())
            else:
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=ctx, timeout=30) as server:
                    server.login(self.username, self.password)
                    server.sendmail(self.username, recipients, msg.as_string())

            logger.info("Email sent to %s: %s", to, subject)
            return {"status": "success", "message": f"Email sent to {to}"}
        except smtplib.SMTPAuthenticationError:
            return {"status": "error", "message": "Authentication failed. Check username/password."}
        except smtplib.SMTPException as exc:
            logger.error("SMTP error: %s", exc)
            return {"status": "error", "message": f"SMTP error: {exc}"}
        except OSError as exc:
            logger.error("Network error sending email: %s", exc)
            return {"status": "error", "message": f"Network error: {exc}"}

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def get_emails(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        unread_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fetch emails from an IMAP folder.

        Args:
            folder: Mailbox folder name (e.g. "INBOX", "Sent").
            limit: Maximum number of emails to return (most recent first).
            unread_only: If True, only return unread messages.

        Returns:
            List of email dicts: {uid, from, to, subject, date, body, read}.
        """
        if not self._configured:
            return [_NOT_CONFIGURED]

        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, timeout=30)
            mail.login(self.username, self.password)
            mail.select(folder)

            criteria = "UNSEEN" if unread_only else "ALL"
            _, data = mail.search(None, criteria)
            ids = data[0].split()

            # Most recent first, limited to `limit`
            ids = ids[-limit:][::-1]

            emails: List[Dict[str, Any]] = []
            for uid in ids:
                _, msg_data = mail.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                parsed = email_lib.message_from_bytes(raw)
                emails.append(self._parse_message(uid.decode(), parsed))

            mail.logout()
            return emails
        except imaplib.IMAP4.error as exc:
            logger.error("IMAP error: %s", exc)
            return [{"status": "error", "message": f"IMAP error: {exc}"}]
        except OSError as exc:
            logger.error("Network error fetching emails: %s", exc)
            return [{"status": "error", "message": f"Network error: {exc}"}]

    def search_emails(self, query: str, folder: str = "INBOX") -> List[Dict[str, Any]]:
        """Search emails by subject or sender.

        Args:
            query: Search string matched against subject or FROM fields.
            folder: Mailbox folder to search.

        Returns:
            List of matching email dicts.
        """
        if not self._configured:
            return [_NOT_CONFIGURED]

        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, timeout=30)
            mail.login(self.username, self.password)
            mail.select(folder)

            # Search by subject or sender
            _, sub_data = mail.search(None, f'SUBJECT "{query}"')
            _, from_data = mail.search(None, f'FROM "{query}"')

            ids_set: set = set()
            for data in (sub_data, from_data):
                if data[0]:
                    ids_set.update(data[0].split())

            emails: List[Dict[str, Any]] = []
            for uid in list(ids_set)[:20]:
                _, msg_data = mail.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                parsed = email_lib.message_from_bytes(raw)
                emails.append(self._parse_message(uid.decode(), parsed))

            mail.logout()
            return emails
        except Exception as exc:
            logger.error("Email search error: %s", exc)
            return [{"status": "error", "message": str(exc)}]

    # ------------------------------------------------------------------
    # Mutation operations
    # ------------------------------------------------------------------

    def delete_email(self, uid: str, folder: str = "INBOX") -> Dict[str, str]:
        """Mark an email for deletion and expunge.

        Args:
            uid: Email UID string.
            folder: Mailbox folder.

        Returns:
            dict with: status, message.
        """
        return self._imap_action(uid, folder, action="delete")

    def mark_read(self, uid: str, folder: str = "INBOX") -> Dict[str, str]:
        """Mark an email as read (\\Seen).

        Args:
            uid: Email UID string.
            folder: Mailbox folder.

        Returns:
            dict with: status, message.
        """
        return self._imap_action(uid, folder, action="seen")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _imap_action(self, uid: str, folder: str, action: str) -> Dict[str, str]:
        if not self._configured:
            return _NOT_CONFIGURED
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, timeout=30)
            mail.login(self.username, self.password)
            mail.select(folder)
            if action == "delete":
                mail.store(uid, "+FLAGS", "\\Deleted")
                mail.expunge()
                result = f"Email {uid} deleted"
            elif action == "seen":
                mail.store(uid, "+FLAGS", "\\Seen")
                result = f"Email {uid} marked as read"
            else:
                result = "Unknown action"
            mail.logout()
            return {"status": "success", "message": result}
        except Exception as exc:
            logger.error("IMAP action %s failed: %s", action, exc)
            return {"status": "error", "message": str(exc)}

    @staticmethod
    def _decode_header(value: str) -> str:
        """Decode RFC 2047-encoded email header."""
        if not value:
            return ""
        parts = email.header.decode_header(value)
        decoded_parts = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded_parts.append(part)
        return "".join(decoded_parts)

    def _parse_message(self, uid: str, msg: email_lib.message.Message) -> Dict[str, Any]:
        """Extract key fields from a parsed email message."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")

        return {
            "uid": uid,
            "from": self._decode_header(msg.get("From", "")),
            "to": self._decode_header(msg.get("To", "")),
            "subject": self._decode_header(msg.get("Subject", "")),
            "date": msg.get("Date", ""),
            "body": body[:2000],
            "read": "\\Seen" in (msg.get("Flags", "") or ""),
        }
