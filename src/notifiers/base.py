from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Notifier(ABC):
    """Abstract base for all alert notifiers."""

    @abstractmethod
    def send(self, show: dict[str, Any], film_name: str) -> bool:
        """Send an alert for a show. Return True on success."""
        ...

    @staticmethod
    def _watch_key(show: dict[str, Any], film_name: str) -> tuple[str, str, str]:
        return str(show.get("theatreId", "")), str(show.get("showDate", "")), film_name

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging."""
        ...
