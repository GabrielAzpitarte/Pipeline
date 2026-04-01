"""Strategy registry — import and register strategies here."""

from __future__ import annotations

from typing import Any, Protocol


class Strategy(Protocol):
    """Interface every strategy must satisfy."""

    def compute_orders(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        """Given market state, return a list of orders."""
        ...


STRATEGIES: dict[str, type[Strategy]] = {}


def register(name: str) -> Any:
    """Decorator to register a strategy class."""

    def wrapper(cls: type[Strategy]) -> type[Strategy]:
        STRATEGIES[name] = cls
        return cls

    return wrapper
