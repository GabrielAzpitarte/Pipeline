from dataclasses import dataclass
from typing import Any


@dataclass
class Listing:
    symbol: str
    product: str
    denomination: str


@dataclass
class Order:
    symbol: str
    price: int
    quantity: int


@dataclass
class OrderDepth:
    buy_orders: dict[int, int]
    sell_orders: dict[int, int]


@dataclass
class Trade:
    symbol: str
    price: int
    quantity: int
    buyer: str
    seller: str
    timestamp: int


@dataclass
class TradingState:
    timestamp: int
    listings: dict[str, Listing]
    order_depths: dict[str, OrderDepth]
    own_trades: dict[str, list[Trade]]
    market_trades: dict[str, list[Trade]]
    position: dict[str, int]
    observations: dict[str, Any]


class Trader:
    def __init__(self):
        # Strategy A (EMERALDS) params
        self.take_edge = 3
        self.order_size = 15
        self.unwind_threshold = 50
        self.alpha = 0.15
        self.inventory_skew = 0.3
        self.ema = {}

        # Strategy B (TOMATOES) params
        self.tom_alpha = 0.15
        self.tom_skew_factor = 0.3
        self.tom_obi_threshold = 0.25
        self.tom_vol_edge = 3
        self.tom_unwind_threshold = 60
        self.tom_ema = {}

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        orders = {}

        for symbol in state.order_depths:
            if symbol == "EMERALDS":
                orders[symbol] = self._emeralds_strategy(symbol, state)
            elif symbol == "TOMATOES":
                orders[symbol] = self._tomatoes_strategy(symbol, state)

        return orders, 0, ""

    def _emeralds_strategy(self, symbol: str, state: TradingState) -> list[Order]:
        depth = state.order_depths[symbol]
        if not depth.buy_orders or not depth.sell_orders:
            return []

        fair = 10000.0
        pos = state.position.get(symbol, 0)
        bb = self._best_bid(depth)
        ba = self._best_ask(depth)

        if bb is None or ba is None:
            return []

        symbol_orders = []

        if abs(pos) > self.unwind_threshold:
            if pos > 0:
                symbol_orders.append(Order(symbol, bb, -min(self.order_size, pos)))
            else:
                symbol_orders.append(Order(symbol, ba, min(self.order_size, -pos)))
        else:
            if ba - fair < -self.take_edge:
                symbol_orders.append(Order(symbol, ba, self.order_size))
            if bb - fair > self.take_edge:
                symbol_orders.append(Order(symbol, bb, -self.order_size))
            if bb + 1 < fair - 1:
                symbol_orders.append(Order(symbol, bb + 1, self.order_size))
            if ba - 1 > fair + 1:
                symbol_orders.append(Order(symbol, ba - 1, -self.order_size))

        return symbol_orders

    def _tomatoes_strategy(self, symbol: str, state: TradingState) -> list[Order]:
        depth = state.order_depths[symbol]
        position = state.position.get(symbol, 0)

        if abs(position) > self.tom_unwind_threshold:
            return self._tomato_unwind_orders(symbol, depth, position)

        microprice = self._volume_weighted_microprice(depth)
        if microprice is None:
            return []

        fair = self.tom_ema.get(symbol, microprice)
        self.tom_ema[symbol] = self.tom_alpha * microprice + (1 - self.tom_alpha) * fair
        skew = -position * self.tom_skew_factor
        fair += skew

        obi = self._order_book_imbalance(depth)
        bb, ba = self._best_bid(depth), self._best_ask(depth)
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

    def _tomato_unwind_orders(self, symbol: str, depth: OrderDepth, position: int) -> list[Order]:
        bb, ba = self._best_bid(depth), self._best_ask(depth)
        if position > 0 and bb is not None:
            return [Order(symbol, bb, -min(position, 20))]
        elif position < 0 and ba is not None:
            return [Order(symbol, ba, min(-position, 20))]
        return []

    def _best_bid(self, depth: OrderDepth) -> int:
        return max(depth.buy_orders.keys()) if depth.buy_orders else None

    def _best_ask(self, depth: OrderDepth) -> int:
        return min(depth.sell_orders.keys()) if depth.sell_orders else None

    def _volume_weighted_microprice(self, depth: OrderDepth) -> float:
        bb, ba = self._best_bid(depth), self._best_ask(depth)
        if bb is None or ba is None:
            return None
        bv = depth.buy_orders.get(bb, 0)
        av = -depth.sell_orders.get(ba, 0)
        return (bb * av + ba * bv) / (bv + av) if bv + av > 0 else (bb + ba) / 2

    def _order_book_imbalance(self, depth: OrderDepth) -> float:
        bb, ba = self._best_bid(depth), self._best_ask(depth)
        if bb is None or ba is None:
            return 0
        bv = depth.buy_orders.get(bb, 0)
        av = -depth.sell_orders.get(ba, 0)
        return (bv - av) / (bv + av) if bv + av > 0 else 0
