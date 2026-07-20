from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Notifier(ABC):
    """Abstract base for all alert notifiers."""

    @abstractmethod
    def send(self, show: dict[str, Any], film_name: str) -> bool:
        """Send an alert for a show. Return True on success."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging."""
        ...
