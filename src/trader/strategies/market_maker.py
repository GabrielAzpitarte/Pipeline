"""Naive market maker — quotes both sides around mid price."""

from __future__ import annotations

from typing import Any

from trader.datamodel import Order, TradingState
from trader.strategies import register
from trader.utils import mid_price_from_depth


@register("market_maker")
class MarketMakerStrategy:
    """Quote buy and sell symmetrically around the mid price."""

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.spread: int = int(p.get("spread", 4))
        self.order_size: int = int(p.get("order_size", 5))

    def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
        """Place symmetric quotes around mid price for each product."""
        orders: dict[str, list[Order]] = {}
        for symbol, depth in state.order_depths.items():
            mid = mid_price_from_depth(depth)
            if mid is None:
                continue
            buy_price = int(mid) - self.spread // 2
            sell_price = int(mid) + self.spread // 2
            orders[symbol] = [
                Order(symbol, buy_price, self.order_size),
                Order(symbol, sell_price, -self.order_size),
            ]
        return orders
