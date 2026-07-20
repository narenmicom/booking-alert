from __future__ import annotations

import smtplib
import time
from email.mime.text import MIMEText
from typing import Any

from src.log import setup_logging
from src.notifiers.base import Notifier

logger = setup_logging()


class EmailNotifier(Notifier):
    """Sends alerts via SMTP email. Optional \u2014 skipped if not configured."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        to_addr: str,
        cooldown_seconds: int = 60,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._to = to_addr
        self._cooldown = cooldown_seconds
        self._last_sent: float = 0.0

    @property
    def name(self) -> str:
        return "Email"

    def is_configured(self) -> bool:
        return bool(self._host and self._user and self._password and self._to)

    def test_connection(self) -> bool:
        """Verify SMTP credentials are valid."""
        if not self.is_configured():
            logger.info("Email: not configured \u2014 skipping (optional)")
            return True

        try:
            with smtplib.SMTP(self._host, self._port, timeout=15) as server:
                server.starttls()
                server.login(self._user, self._password)
            logger.info("Email: SMTP login successful to %s", self._host)
            return True
        except smtplib.SMTPException as e:
            logger.error("Email: SMTP connection failed \u2014 %s", e)
            return False

    def send(self, show: dict[str, Any], film_name: str) -> bool:
        if not self.is_configured():
            logger.debug("Email not configured \u2014 skipping")
            return False

        now = time.time()
        if now - self._last_sent < self._cooldown:
            logger.debug("Email rate-limited \u2014 skipping")
            return False

        body = self._format_body(show, film_name)

        try:
            msg = MIMEText(body, "plain")
            msg["From"] = self._user
            msg["To"] = self._to
            msg["Subject"] = f"\U0001f3ac Booking Alert \u2014 {film_name}"

            with smtplib.SMTP(self._host, self._port, timeout=15) as server:
                server.starttls()
                server.login(self._user, self._password)
                server.send_message(msg)

            self._last_sent = time.time()
            logger.info("Email alert sent for %s", film_name)
            return True
        except smtplib.SMTPException as e:
            logger.error("Email send failed: %s", e)
            return False

    @staticmethod
    def _format_body(show: dict[str, Any], film_name: str) -> str:
        theatre = show.get("screenName", "Unknown")
        show_time = show.get("showTime", "Unknown")
        status = show.get("statusTxt", "")
        lang = show.get("language", "")
        fmt = show.get("filmFormat", "") or show.get("screenType", "")
        sid = show.get("sessionId", "?")

        lines = [f"Movie: {film_name}"]
        lines.append(f"Screen: {theatre}")
        lines.append(f"Time: {show_time}")
        if fmt:
            lines.append(f"Format: {fmt}")
        if lang:
            lines.append(f"Language: {lang}")
        if status:
            lines.append(f"Status: {status}")
        lines.append(f"Session ID: {sid}")
        lines.append("")
        lines.append("https://www.pvrcinemas.com")
        return "\n".join(lines)
