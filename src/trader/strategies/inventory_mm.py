"""Inventory-aware market maker — skews quotes based on position."""

from __future__ import annotations

from typing import Any

from trader.datamodel import Order, TradingState
from trader.strategies import register
from trader.utils import mid_price_from_depth


@register("inventory_mm")
class InventoryMMStrategy:
    """Market maker that adjusts quotes to manage inventory risk.

    When long, both quotes shift down (encourage selling).
    When short, both quotes shift up (encourage buying).
    """

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.base_spread: int = int(p.get("base_spread", 4))
        self.order_size: int = int(p.get("order_size", 5))
        self.skew_factor: float = float(p.get("skew_factor", 1.0))

    def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
        """Quote both sides, skewing away from current inventory."""
        orders: dict[str, list[Order]] = {}
        for symbol, depth in state.order_depths.items():
            mid = mid_price_from_depth(depth)
            if mid is None:
                continue
            pos = state.position.get(symbol, 0)
            skew = int(pos * self.skew_factor)
            half = self.base_spread // 2
            buy_price = int(mid) - half - skew
            sell_price = int(mid) + half - skew
            orders[symbol] = [
                Order(symbol, buy_price, self.order_size),
                Order(symbol, sell_price, -self.order_size),
            ]
        return orders
