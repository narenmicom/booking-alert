from __future__ import annotations

import time
from typing import Any

import requests

from src.log import setup_logging
from src.notifiers.base import Notifier

logger = setup_logging()


class TelegramNotifier(Notifier):
    """Sends alerts via a Telegram bot using the HTTP Bot API.

    Auto-discovers chat IDs from getUpdates so any chat that has
    messaged the bot will receive alerts.
    """

    def __init__(
        self,
        bot_token: str,
        cooldown_seconds: int = 60,
    ) -> None:
        self._token = bot_token
        self._cooldown = cooldown_seconds
        self._last_sent: float = 0.0
        self._chat_ids: list[str] = []

    @property
    def name(self) -> str:
        return "Telegram"

    def discover_chat_ids(self) -> list[str]:
        """Poll getUpdates to find all chats that have messaged the bot."""
        if not self._token:
            return []

        url = f"https://api.telegram.org/bot{self._token}/getUpdates"
        chat_ids: set[str] = set()

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Telegram getUpdates failed: %s", e)
            return self._chat_ids

        if not data.get("ok"):
            logger.error("Telegram getUpdates returned not-ok: %s", data)
            return self._chat_ids

        for update in data.get("result", []):
            msg = update.get("message") or update.get("edited_message") or {}
            chat = msg.get("chat", {})
            cid = chat.get("id")
            if cid is not None:
                chat_ids.add(str(cid))

        self._chat_ids = sorted(chat_ids)
        if self._chat_ids:
            logger.info("Discovered %d Telegram chat(s)", len(self._chat_ids))
        else:
            logger.warning("No Telegram chats found \u2014 send a message to the bot first")
        return self._chat_ids

    def test_connection(self) -> bool:
        """Verify the bot token is valid and Telegram API is reachable."""
        if not self._token:
            logger.error("Telegram: TELEGRAM_BOT_TOKEN not set in .env")
            return False

        url = f"https://api.telegram.org/bot{self._token}/getMe"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Telegram: API unreachable \u2014 %s", e)
            return False

        if not data.get("ok"):
            logger.error("Telegram: bot token invalid \u2014 %s", data.get("description", "unknown error"))
            return False

        bot = data.get("result", {})
        logger.info(
            "Telegram: connected as @%s (%s)",
            bot.get("username", "?"),
            bot.get("first_name", "?"),
        )
        return True

    def send_test_message(self) -> bool:
        """Send a test message to all discovered chats."""
        if not self._chat_ids:
            logger.warning("Telegram: no chats to send test to \u2014 message the bot first")
            return False

        text = "\u2705 <b>Booking Alert test</b>\nConnection successful."
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        sent_any = False

        for cid in self._chat_ids:
            payload = {"chat_id": cid, "text": text, "parse_mode": "HTML"}
            try:
                resp = requests.post(url, json=payload, timeout=10)
                resp.raise_for_status()
                sent_any = True
                logger.info("Telegram: test message sent to chat %s", cid)
            except requests.RequestException as e:
                logger.error("Telegram: test message to chat %s failed \u2014 %s", cid, e)

        return sent_any

    def send(self, show: dict[str, Any], film_name: str) -> bool:
        if not self._token:
            logger.warning("Telegram not configured \u2014 skipping")
            return False

        if not self._chat_ids:
            logger.warning("No Telegram chats discovered \u2014 skipping")
            return False

        now = time.time()
        if now - self._last_sent < self._cooldown:
            logger.debug("Telegram rate-limited \u2014 skipping")
            return False

        message = self._format_message(show, film_name)
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        sent_any = False

        for cid in self._chat_ids:
            payload = {
                "chat_id": cid,
                "text": message,
                "parse_mode": "HTML",
            }
            try:
                resp = requests.post(url, json=payload, timeout=10)
                resp.raise_for_status()
                sent_any = True
                logger.info("Telegram alert sent to chat %s for %s", cid, film_name)
            except requests.RequestException as e:
                logger.error("Telegram send to chat %s failed: %s", cid, e)

        if sent_any:
            self._last_sent = time.time()
        return sent_any

    @staticmethod
    def _format_message(show: dict[str, Any], film_name: str) -> str:
        theatre = show.get("screenName", "Unknown")
        show_time = show.get("showTime", "Unknown")
        status = show.get("statusTxt", "")
        lang = show.get("language", "")
        fmt = show.get("filmFormat", "") or show.get("screenType", "")
        sid = show.get("sessionId", "?")
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        lines = [f"\U0001f3ac <b>{film_name}</b>"]
        lines.append(f"\U0001f4cd Screen: {theatre}")
        lines.append(f"\u23f0 Time: {show_time}")
        if fmt:
            lines.append(f"\U0001f39e\ufe0f Format: {fmt}")
        if lang:
            lines.append(f"\U0001f1ec\U0001f1e7 Language: {lang}")
        if status:
            lines.append(f"\u2139\ufe0f Status: {status}")
        lines.append(f"\U0001f194 ID: {sid}")
        lines.append(f"\U0001f552 Alerted at: {now_str}")
        return "\n".join(lines)
