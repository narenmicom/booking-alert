#!/usr/bin/env python3
"""
Booking Alert \u2014 polls PVR API for film sessions and sends alerts.

Usage:
    python -m src.main                  # run the poller
    python -m src.main --test           # test connectivity to PVR + Telegram + Email
    python -m src.main --test-telegram  # send a Telegram test message
"""

from __future__ import annotations

import os
import signal
import sys
import threading
from datetime import date

from src.api import test_api_connection
from src.config import load_config
from src.log import setup_logging, add_betterstack_handler
from src.notifiers import TelegramNotifier, EmailNotifier
from src.poller import build_date_film_map, poll_loop

logger = setup_logging()


def test_telegram(bot_token: str) -> bool:
    logger.info("=== Testing Telegram ===")
    telegram = TelegramNotifier(bot_token=bot_token)
    if not telegram.test_connection():
        return False
    telegram.discover_chat_ids()
    return telegram.send_test_message()


def run_test(config) -> int:
    """Test connectivity to all configured services. Returns exit code."""
    failures = 0

    # 1. PVR API
    logger.info("=== Testing PVR API ===")
    fallback_date = next(iter(config.pvr.dates), date.today().isoformat())
    test_date = next(iter(build_date_film_map(config)), fallback_date)
    for cid in config.pvr.cids:
        logger.info("Testing PVR cinema %s for %s", cid, test_date)
        if not test_api_connection(
            url=config.pvr.url,
            city=config.pvr.city,
            cid=cid,
            lat=config.pvr.lat,
            lng=config.pvr.lng,
            date=test_date,
        ):
            failures += 1

    # 2. Telegram
    if not test_telegram(config.telegram_bot_token):
        failures += 1

    # 3. Email
    logger.info("=== Testing Email ===")
    email = EmailNotifier(
        host=config.smtp_host,
        port=config.smtp_port,
        user=config.smtp_user,
        password=config.smtp_password,
        to_addr=config.alert_email_to,
    )
    if not email.test_connection():
        failures += 1

    logger.info("=== Test summary ===")
    if failures == 0:
        logger.info("All checks passed \u2705")
        return 0
    logger.error("%d check(s) failed \u274c", failures)
    return 1


def main() -> None:
    args = sys.argv[1:]
    if "--test-telegram" in args:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        sys.exit(0 if test_telegram(bot_token) else 1)

    test_mode = "--test" in args or "-test" in args

    config = load_config()

    # Enable Better Stack logging if configured
    add_betterstack_handler(
        source_token=config.betterstack_source_token,
        ingesting_host=config.betterstack_ingesting_host,
    )

    if test_mode:
        sys.exit(run_test(config))

    # Validate config
    if not config.films:
        logger.warning("No films configured in config.yaml \u2014 nothing to watch")
        sys.exit(0)

    if not build_date_film_map(config):
        logger.warning("No dates configured for any film \u2014 nothing to poll")
        sys.exit(0)

    # Build notifiers
    notifiers = []

    tg = TelegramNotifier(
        bot_token=config.telegram_bot_token,
    )
    tg.discover_chat_ids()
    notifiers.append(tg)

    email = EmailNotifier(
        host=config.smtp_host,
        port=config.smtp_port,
        user=config.smtp_user,
        password=config.smtp_password,
        to_addr=config.alert_email_to,
    )
    if email.is_configured():
        notifiers.append(email)
    else:
        logger.info("Email not configured \u2014 skipping email alerts")

    logger.info(
        "Notifiers: %s",
        ", ".join(n.name for n in notifiers),
    )

    # Graceful shutdown via signal
    stop_event = threading.Event()

    def _handle_signal(signum, frame):
        logger.info("Received signal %s \u2014 shutting down...", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Start polling (blocks until stop)
    try:
        poll_loop(config, notifiers, stop_event)
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
