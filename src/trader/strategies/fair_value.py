"""Fair value trader — places limit orders edge ticks from fair value."""

from __future__ import annotations

from typing import Any

from trader.datamodel import Order, TradingState
from trader.strategies import register
from trader.utils import mid_price_from_depth


@register("fair_value")
class FairValueStrategy:
    """Estimate fair value from mid price, quote at fair +/- edge."""

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.edge: int = int(p.get("edge", 2))
        self.order_size: int = int(p.get("order_size", 5))

    def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
        """Place buy at fair-edge, sell at fair+edge for each product."""
        orders: dict[str, list[Order]] = {}
        for symbol, depth in state.order_depths.items():
            fair = mid_price_from_depth(depth)
            if fair is None:
                continue
            buy_price = int(fair) - self.edge
            sell_price = int(fair) + self.edge
            orders[symbol] = [
                Order(symbol, buy_price, self.order_size),
                Order(symbol, sell_price, -self.order_size),
            ]
        return orders
