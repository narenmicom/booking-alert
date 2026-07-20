from __future__ import annotations

import threading
from typing import List

from src.api import fetch_sessions, PvrApiError
from src.config import Config
from src.filter import find_matching_shows
from src.log import setup_logging
from src.notifiers.base import Notifier

logger = setup_logging()


def poll_loop(
    config: Config,
    notifiers: List[Notifier],
    stop_event: threading.Event,
) -> None:
    """
    Main polling loop \u2014 runs every POLL_INTERVAL seconds.
    Fetches sessions for all configured dates, checks for target films,
    and sends alerts for all matching shows every cycle.
    """
    logger.info(
        "Polling started \u2014 interval=%ds, films=%s, dates=%s",
        config.poll_interval_seconds,
        [f.name for f in config.films],
        config.pvr.dates,
    )

    while not stop_event.is_set():
        _run_cycle(config, notifiers)
        stop_event.wait(timeout=config.poll_interval_seconds)

    logger.info("Polling stopped gracefully")


def _run_cycle(
    config: Config,
    notifiers: List[Notifier],
) -> None:
    """Single poll cycle: fetch for each date \u2192 filter \u2192 alert."""
    all_matches: list[tuple] = []

    for date in config.pvr.dates:
        try:
            response = fetch_sessions(
                url=config.pvr.url,
                city=config.pvr.city,
                cid=config.pvr.cid,
                lat=config.pvr.lat,
                lng=config.pvr.lng,
                date=date,
            )
        except PvrApiError as e:
            logger.error(str(e))
            continue

        matches = find_matching_shows(response, config.films)
        all_matches.extend(matches)

    if not all_matches:
        logger.info("No matching shows found")
        return

    logger.info("Found %d matching show(s) \u2014 alerting", len(all_matches))

    for film, show in all_matches:
        sid = str(show.get("sessionId", "?"))
        for notifier in notifiers:
            try:
                notifier.send(show, film.name)
            except Exception as e:
                logger.error(
                    "[%s] Error alerting show %s: %s",
                    notifier.name,
                    sid,
                    e,
                )
