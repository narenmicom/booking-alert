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
    Parse the API response and find all shows whose movieId matches
    any of the watched films.

    Returns list of (FilmWatch, show_dict) tuples.
    """
    target_ids = {f.id for f in films}
    id_to_film = {f.id: f for f in films}

    results: List[Tuple[FilmWatch, Dict[str, Any]]] = []

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

        # Check if this movie group has any of our target filmIds
        movie_re = cinema_movie.get("movieRe", {})
        films_list = movie_re.get("films", [])
        matched_film_ids = set()

        for f in films_list:
            fid = str(f.get("filmId", ""))
            if fid in target_ids:
                matched_film_ids.add(fid)

        if not matched_film_ids:
            continue

        # Collect shows from experienceSessions where movieId matches
        experience_sessions = cinema_movie.get("experienceSessions", [])
        for exp_grp in experience_sessions:
            if not isinstance(exp_grp, dict):
                continue
            shows = exp_grp.get("shows", [])
            for show in shows:
                show_movie_id = str(show.get("movieId", ""))
                if show_movie_id in matched_film_ids:
                    results.append((id_to_film[show_movie_id], show))

    if results:
        logger.info("Found %d matching show(s)", len(results))

    return results
