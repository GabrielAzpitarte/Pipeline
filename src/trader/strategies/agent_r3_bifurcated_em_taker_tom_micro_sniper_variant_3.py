from __future__ import annotations

from typing import Any

from trader.datamodel import Order, TradingState
from trader.strategies import register
from trader.utils import best_ask, best_bid


@register("agent_r3_bifurcated_em_taker_tom_micro_sniper")
class BifurcatedEmTakerTomMicroSniper:
    """Asset-specific hybrid strategy maximizing per-asset fills."""

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.order_size: int = int(p.get("order_size", 14))
        self.unwind_threshold: int = int(p.get("unwind_threshold", 57))
        self.tom_alpha: float = float(p.get("tom_alpha", 0.1723))
        self.tom_skew_factor: float = float(p.get("tom_skew_factor", 0.2973))
        self.tom_obi_threshold: float = float(p.get("tom_obi_threshold", 0.2752))
        self.tom_vol_edge: int = int(p.get("tom_vol_edge", 3))
        self.tom_ema: dict[str, float] = {}

    def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
        orders: dict[str, list[Order]] = {}
        for symbol, depth in state.order_depths.items():
            position = state.position.get(symbol, 0)
            if abs(position) > self.unwind_threshold:
                orders[symbol] = self._unwind_orders(symbol, depth, position)
                continue
            if symbol == "EMERALDS":
                orders[symbol] = self._emerald_orders(depth, position)
            elif symbol == "TOMATOES":
                orders[symbol] = self._tomato_orders(symbol, depth, position)
        return orders

    def _emerald_orders(self, depth, position: int) -> list[Order]:
        bb, ba = best_bid(depth), best_ask(depth)
        if bb is None or ba is None:
            return []
        buy_price = min(bb + 1, 9999)
        sell_price = max(ba - 1, 10001)
        return [
            Order("EMERALDS", buy_price, self.order_size),
            Order("EMERALDS", sell_price, -self.order_size),
        ]

    def _tomato_orders(self, symbol: str, depth, position: int) -> list[Order]:
        microprice = self._volume_weighted_microprice(depth)
        if microprice is None:
            return []
        fair = self.tom_ema.get(symbol, microprice)
        self.tom_ema[symbol] = self.tom_alpha * microprice + (1 - self.tom_alpha) * fair
        skew = -position * self.tom_skew_factor
        fair += skew
        obi = self._order_book_imbalance(depth)
        bb, ba = best_bid(depth), best_ask(depth)
        if bb is None or ba is None:
            return []
        orders = []
        if abs(obi) < self.tom_obi_threshold:
            orders.append(Order(symbol, bb + 1, self.order_size))
            orders.append(Order(symbol, ba - 1, -self.order_size))
        edge = self.tom_vol_edge * max(1, int((ba - bb) / 4))
        orders.append(Order(symbol, int(fair - edge), self.order_size))
        orders.append(Order(symbol, int(fair + edge), -self.order_size))
        return orders

    def _unwind_orders(self, symbol: str, depth, position: int) -> list[Order]:
        bb, ba = best_bid(depth), best_ask(depth)
        if position > 0 and bb is not None:
            return [Order(symbol, bb, -min(position, 20))]
        elif position < 0 and ba is not None:
            return [Order(symbol, ba, min(-position, 20))]
        return []

    def _volume_weighted_microprice(self, depth) -> float | None:
        bb, ba = best_bid(depth), best_ask(depth)
        if bb is None or ba is None:
            return None
        bv = depth.buy_orders.get(bb, 0)
        av = -depth.sell_orders.get(ba, 0)
        return (bb * av + ba * bv) / (bv + av) if bv + av > 0 else (bb + ba) / 2

    def _order_book_imbalance(self, depth) -> float:
        bb, ba = best_bid(depth), best_ask(depth)
        if bb is None or ba is None:
            return 0
        bv = depth.buy_orders.get(bb, 0)
        av = -depth.sell_orders.get(ba, 0)
        return (bv - av) / (bv + av) if bv + av > 0 else 0
