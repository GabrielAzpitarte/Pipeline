"""No-op strategy — returns no orders. Used as baseline and test fixture."""

from __future__ import annotations

from trader.datamodel import Order, TradingState
from trader.strategies import register


@register("noop")
class NoopStrategy:
    """Does nothing. Returns empty orders for all products."""

    def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
        """Return no orders."""
        return {}
