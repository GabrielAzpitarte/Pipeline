"""Two-phase order matching with queue position modeling.

Phase 1: Match orders aggressively against the order book.
Phase 2: Match remaining quantity against market trades with queue modeling.

Queue position modeling (ported from GeyzsoN Rust backtester):
- Your passive order joins the BACK of the queue at its price level
- Existing book volume at that level gets filled FIRST
- You only get fills from overflow after the queue is exhausted
- At strictly better prices, no queue — direct fill
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from trader.datamodel import Order, OrderDepth, Trade


class TradeMatchingMode(Enum):
    """How to handle market trade matching in Phase 2."""

    ALL = "all"
    WORSE = "worse"
    NONE = "none"


@dataclass
class Fill:
    """A single fill resulting from order matching."""

    symbol: str
    price: int
    quantity: int  # positive = bought, negative = sold
    against: str  # "book" or "market_trade"


@dataclass
class MarketTrade:
    """Wrapper tracking available buy/sell quantities for a market trade."""

    trade: Trade
    buy_quantity: int  # available for sell orders to match against
    sell_quantity: int  # available for buy orders to match against


def match_buy_order(
    order: Order,
    depth: OrderDepth,
    market_trades: list[MarketTrade],
    mode: TradeMatchingMode = TradeMatchingMode.ALL,
    buy_queue_remaining: dict[int, int] | None = None,
) -> list[Fill]:
    """Match a buy order against sell side of book + market trades.

    Phase 1: Cross against asks at or below order price.
    Phase 2: Match against market trades with queue position modeling.
    """
    remaining = order.quantity
    fills: list[Fill] = []

    # Phase 1: order book crossing
    for ask_price in sorted(depth.sell_orders.keys()):
        if remaining <= 0:
            break
        if ask_price > order.price:
            break
        available = abs(depth.sell_orders[ask_price])
        fill_qty = min(remaining, available)
        fills.append(Fill(symbol=order.symbol, price=ask_price, quantity=fill_qty, against="book"))
        depth.sell_orders[ask_price] += fill_qty
        if depth.sell_orders[ask_price] == 0:
            del depth.sell_orders[ask_price]
        remaining -= fill_qty

    # Phase 2: market trades with queue position modeling
    if remaining > 0 and mode != TradeMatchingMode.NONE:
        for mt in market_trades:
            if remaining <= 0:
                break
            if mt.sell_quantity <= 0:
                continue

            # Price eligibility
            if mt.trade.price > order.price:
                continue
            if mode == TradeMatchingMode.WORSE and mt.trade.price == order.price:
                continue

            # Queue consumption: at the SAME price, existing book gets filled first
            if mt.trade.price == order.price and buy_queue_remaining is not None:
                ahead = buy_queue_remaining.get(order.price, 0)
                if ahead > 0:
                    consumed = min(mt.sell_quantity, ahead)
                    mt.sell_quantity -= consumed
                    buy_queue_remaining[order.price] -= consumed
                    if buy_queue_remaining[order.price] <= 0:
                        buy_queue_remaining.pop(order.price, None)

            # Fill from whatever's left after queue consumption
            if mt.sell_quantity <= 0:
                continue
            fill_qty = min(remaining, mt.sell_quantity)
            fills.append(
                Fill(
                    symbol=order.symbol,
                    price=order.price,
                    quantity=fill_qty,
                    against="market_trade",
                )
            )
            mt.sell_quantity -= fill_qty
            remaining -= fill_qty

    return fills


def match_sell_order(
    order: Order,
    depth: OrderDepth,
    market_trades: list[MarketTrade],
    mode: TradeMatchingMode = TradeMatchingMode.ALL,
    sell_queue_remaining: dict[int, int] | None = None,
) -> list[Fill]:
    """Match a sell order against buy side of book + market trades.

    Phase 1: Cross against bids at or above order price.
    Phase 2: Match against market trades with queue position modeling.
    """
    remaining = abs(order.quantity)
    fills: list[Fill] = []

    # Phase 1: order book crossing
    for bid_price in sorted(depth.buy_orders.keys(), reverse=True):
        if remaining <= 0:
            break
        if bid_price < order.price:
            break
        available = depth.buy_orders[bid_price]
        fill_qty = min(remaining, available)
        fills.append(Fill(symbol=order.symbol, price=bid_price, quantity=-fill_qty, against="book"))
        depth.buy_orders[bid_price] -= fill_qty
        if depth.buy_orders[bid_price] == 0:
            del depth.buy_orders[bid_price]
        remaining -= fill_qty

    # Phase 2: market trades with queue position modeling
    if remaining > 0 and mode != TradeMatchingMode.NONE:
        for mt in market_trades:
            if remaining <= 0:
                break
            if mt.buy_quantity <= 0:
                continue

            # Price eligibility
            if mt.trade.price < order.price:
                continue
            if mode == TradeMatchingMode.WORSE and mt.trade.price == order.price:
                continue

            # Queue consumption: at the SAME price, existing book gets filled first
            if mt.trade.price == order.price and sell_queue_remaining is not None:
                ahead = sell_queue_remaining.get(order.price, 0)
                if ahead > 0:
                    consumed = min(mt.buy_quantity, ahead)
                    mt.buy_quantity -= consumed
                    sell_queue_remaining[order.price] -= consumed
                    if sell_queue_remaining[order.price] <= 0:
                        sell_queue_remaining.pop(order.price, None)

            # Fill from whatever's left
            if mt.buy_quantity <= 0:
                continue
            fill_qty = min(remaining, mt.buy_quantity)
            fills.append(
                Fill(
                    symbol=order.symbol,
                    price=order.price,
                    quantity=-fill_qty,
                    against="market_trade",
                )
            )
            mt.buy_quantity -= fill_qty
            remaining -= fill_qty

    return fills


def match_orders(
    orders: dict[str, list[Order]],
    depths: dict[str, OrderDepth],
    market_trades: dict[str, list[MarketTrade]],
    mode: TradeMatchingMode = TradeMatchingMode.ALL,
    buy_queues: dict[str, dict[int, int]] | None = None,
    sell_queues: dict[str, dict[int, int]] | None = None,
) -> dict[str, list[Fill]]:
    """Match all orders with queue position modeling."""
    all_fills: dict[str, list[Fill]] = {}

    for symbol, order_list in orders.items():
        depth = depths.get(symbol)
        if depth is None:
            depth = OrderDepth()
        trades_for_sym = market_trades.get(symbol, [])
        bq = buy_queues.get(symbol, {}) if buy_queues else {}
        sq = sell_queues.get(symbol, {}) if sell_queues else {}
        symbol_fills: list[Fill] = []

        for order in order_list:
            if order.quantity > 0:
                fills = match_buy_order(order, depth, trades_for_sym, mode, bq or None)
            elif order.quantity < 0:
                fills = match_sell_order(order, depth, trades_for_sym, mode, sq or None)
            else:
                continue
            symbol_fills.extend(fills)

        if symbol_fills:
            all_fills[symbol] = symbol_fills

    return all_fills
