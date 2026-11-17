from __future__ import annotations

import threading
from collections import OrderedDict
from itertools import product
from typing import Dict, List

from src.api import fetch_sessions, PvrApiError
from src.config import Config, FilmWatch
from src.filter import find_matching_shows
from src.log import setup_logging
from src.notifiers.base import Notifier

logger = setup_logging()


def _effective_dates(film: FilmWatch, global_dates: List[str]) -> List[str]:
    """Per-film dates override the global fallback when set."""
    return film.dates if film.dates else list(global_dates)


def build_date_film_map(config: Config) -> "OrderedDict[str, List[FilmWatch]]":
    """Map each unique effective date to the films interested in it."""
    date_to_films: "OrderedDict[str, List[FilmWatch]]" = OrderedDict()
    for film in config.films:
        for date in _effective_dates(film, config.pvr.dates):
            date_to_films.setdefault(date, []).append(film)
    return date_to_films


def poll_loop(
    config: Config,
    notifiers: List[Notifier],
    stop_event: threading.Event,
) -> None:
    """
    Main polling loop \u2014 runs every POLL_INTERVAL seconds.
    Fetches sessions for each watched date and cinema and alerts on matching shows.
    """
    date_to_films = build_date_film_map(config)

    logger.info(
        "Polling started \u2014 interval=%ds, cinemas=%s, dates=%s",
        config.poll_interval_seconds,
        config.pvr.cids,
        {d: [f.name for f in fs] for d, fs in date_to_films.items()},
    )

    while not stop_event.is_set():
        _run_cycle(config, notifiers, date_to_films)
        stop_event.wait(timeout=config.poll_interval_seconds)

    logger.info("Polling stopped gracefully")


def _run_cycle(
    config: Config,
    notifiers: List[Notifier],
    date_to_films: Dict[str, List[FilmWatch]],
) -> None:
    """Fetch and check each cinema and date pair."""
    all_matches = []

    for (date, films_for_date), cid in product(date_to_films.items(), config.pvr.cids):
        try:
            response = fetch_sessions(
                url=config.pvr.url,
                city=config.pvr.city,
                cid=cid,
                lat=config.pvr.lat,
                lng=config.pvr.lng,
                date=date,
            )
        except PvrApiError as e:
            logger.error("Cinema %s: %s", cid, e)
            continue

        for film, show in find_matching_shows(response, films_for_date):
            if str(show.get("theatreId") or cid) != cid:
                continue
            if (show.get("showDate") or date) != date:
                continue
            all_matches.append((film, {**show, "theatreId": cid, "showDate": date}))

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
