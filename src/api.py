from __future__ import annotations

from typing import Any

import requests

from src.log import setup_logging

logger = setup_logging()


class PvrApiError(Exception):
    """Raised when the PVR API call fails."""


def fetch_sessions(
    url: str,
    city: str,
    cid: str,
    lat: str,
    lng: str,
    date: str,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    POST to the PVR sessions API for a given date.
    Returns the full JSON response dict.
    """
    headers = {
        "Origin": "https://www.pvrcinemas.com",
        "City": city,
        "appversion": "1.0",
        "platform": "WEBSITE",
        "Content-Type": "application/json",
    }
    body = {
        "city": city,
        "cid": cid,
        "lat": lat,
        "lng": lng,
        "dated": date,
        "qr": "NO",
        "cineType": "",
        "cineTypeQR": "",
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise PvrApiError(f"API request failed for {date}: {e}") from e
    except ValueError as e:
        raise PvrApiError(f"Invalid JSON response for {date}: {e}") from e

    return data


def test_api_connection(
    url: str,
    city: str,
    cid: str,
    lat: str,
    lng: str,
    date: str,
) -> bool:
    """Verify outbound connectivity to the PVR API."""
    try:
        response = fetch_sessions(
            url=url, city=city, cid=cid, lat=lat, lng=lng, date=date,
        )
    except PvrApiError as e:
        logger.error("PVR API: connection failed \u2014 %s", e)
        return False

    status = response.get("status")
    result = response.get("result")
    msg = response.get("msg", "")

    if status == 500 and result == "error":
        logger.info("PVR API: reachable (no bookings for %s \u2014 %s)", date, msg)
        return True

    output = response.get("output")
    if output and isinstance(output, dict):
        sessions = output.get("cinemaMovieSessions") or []
        logger.info(
            "PVR API: reachable \u2014 %d movie session group(s) for %s",
            len(sessions),
            date,
        )
    else:
        logger.info("PVR API: reachable \u2014 response received for %s", date)
    return True
