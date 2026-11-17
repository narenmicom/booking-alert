from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.config import FilmWatch
from src.log import setup_logging

logger = setup_logging()


def find_matching_shows(
    response: dict[str, Any],
    films: List[FilmWatch],
) -> List[Tuple[FilmWatch, dict[str, Any]]]:
    """
    Parse the API response and find shows for the watched films.

    Films with any ``ids`` are matched by ``filmId``/``movieId``. Films
    without ``ids`` are matched by a case-insensitive substring search
    of their ``name`` against the movie group's name in the response;
    all shows under a matched movie group are returned for such films.

    Returns list of (FilmWatch, show_dict) tuples, de-duplicated by sessionId.
    """
    id_films = [f for f in films if f.ids]
    name_films = [f for f in films if not f.ids]

    target_ids = {fid for f in id_films for fid in f.ids}
    id_to_film: Dict[str, FilmWatch] = {}
    for f in id_films:
        for fid in f.ids:
            id_to_film[fid] = f

    results: List[Tuple[FilmWatch, Dict[str, Any]]] = []
    seen_sessions: set[str] = set()

    # Navigate: output -> cinemaMovieSessions[]
    output = response.get("output")
    if output is None:
        # API returns output: null when no bookings exist for the date
        logger.info("No bookings available for this date")
        return results
    if not isinstance(output, dict):
        logger.warning("Unexpected output structure: %s", type(output).__name__)
        return results

    movie_sessions = output.get("cinemaMovieSessions")
    if movie_sessions is None:
        logger.info("No cinema movie sessions for this date")
        return results
    if not isinstance(movie_sessions, list):
        logger.warning("Unexpected cinemaMovieSessions structure")
        return results

    for cinema_movie in movie_sessions:
        if not isinstance(cinema_movie, dict):
            continue

        movie_re = cinema_movie.get("movieRe", {})
        if not isinstance(movie_re, dict):
            movie_re = {}

        # --- ID-based matching: collect target filmIds present here ---
        matched_film_ids = set()

        if target_ids:
            for f in movie_re.get("films") or []:
                if isinstance(f, dict) and (fid := str(f.get("filmId", ""))) in target_ids:
                    matched_film_ids.add(fid)

        # --- Name-based matching: films matched by movie name substring ---
        matched_name_films: List[FilmWatch] = []
        if name_films:
            movie_name_text = " ".join(
                str(movie_re.get(key, ""))
                for key in ("name", "movieName", "title", "filmName")
            ).lower()
            for nf in name_films:
                if nf.name and nf.name.lower() in movie_name_text:
                    matched_name_films.append(nf)

        if not matched_film_ids and not matched_name_films:
            continue

        experience_sessions = cinema_movie.get("experienceSessions") or []
        for exp_grp in experience_sessions:
            if not isinstance(exp_grp, dict):
                continue
            shows = exp_grp.get("shows") or []
            for show in shows:
                if not isinstance(show, dict):
                    continue
                sid = str(show.get("sessionId", ""))
                if sid in seen_sessions:
                    continue

                # ID-based: only shows whose movieId matches
                show_movie_id = str(show.get("movieId", ""))
                if show_movie_id in matched_film_ids:
                    results.append((id_to_film[show_movie_id], show))
                    seen_sessions.add(sid)
                    continue

                # Name-based: any show under a matched movie group
                if matched_name_films:
                    results.append((matched_name_films[0], show))
                    seen_sessions.add(sid)

    if results:
        logger.info("Found %d matching show(s)", len(results))

    return results
