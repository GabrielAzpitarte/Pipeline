"""Main Trader class that dispatches to a strategy and enforces risk."""

from __future__ import annotations

from typing import Any


class Trader:
    """Receives market state, delegates to a strategy, filters through risk."""

    def __init__(self, strategy_name: str = "noop") -> None:
        self.strategy_name = strategy_name

    def on_tick(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        """Process one tick of market data and return orders."""
        return []
