"""Two-phase order matching for the local simulator.

Phase 1: Match orders aggressively against the order book.
Phase 2: Match remaining quantity against market trades (at YOUR price).

Matching semantics match jmerle/prosperity4bt — the most-used backtester
in the IMC Prosperity competition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from trader.datamodel import Order, OrderDepth, Trade


class TradeMatchingMode(Enum):
    """How to handle market trade matching in Phase 2."""

    ALL = "all"  # Match trades at prices equal or better than your quote
    WORSE = "worse"  # Only match trades strictly better than your quote
    NONE = "none"  # Skip market trade matching entirely


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
) -> list[Fill]:
    """Match a buy order against sell side of book + market trades.

    Phase 1: Cross against asks at or below order price. Fill at ask price.
    Phase 2: Match against market trades. Fill at YOUR order price.
    """
    remaining = order.quantity
    fills: list[Fill] = []

    # Phase 1: order book
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

    # Phase 2: market trades (jmerle semantics)
    if remaining > 0 and mode != TradeMatchingMode.NONE:
        for mt in market_trades:
            if remaining <= 0:
                break
            if mt.sell_quantity <= 0:
                continue
            # Price eligibility (matching jmerle exactly)
            if mt.trade.price > order.price:
                continue
            if mode == TradeMatchingMode.WORSE and mt.trade.price == order.price:
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
) -> list[Fill]:
    """Match a sell order against buy side of book + market trades.

    Phase 1: Cross against bids at or above order price. Fill at bid price.
    Phase 2: Match against market trades. Fill at YOUR order price.
    """
    remaining = abs(order.quantity)
    fills: list[Fill] = []

    # Phase 1: order book
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

    # Phase 2: market trades (jmerle semantics)
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
) -> dict[str, list[Fill]]:
    """Match all orders for all symbols against their respective books.

    The depth and market_trades are mutated during matching.
    """
    all_fills: dict[str, list[Fill]] = {}

    for symbol, order_list in orders.items():
        depth = depths.get(symbol)
        if depth is None:
            depth = OrderDepth()
        trades_for_sym = market_trades.get(symbol, [])
        symbol_fills: list[Fill] = []

        for order in order_list:
            if order.quantity > 0:
                fills = match_buy_order(order, depth, trades_for_sym, mode)
            elif order.quantity < 0:
                fills = match_sell_order(order, depth, trades_for_sym, mode)
            else:
                continue
            symbol_fills.extend(fills)

        if symbol_fills:
            all_fills[symbol] = symbol_fills

    return all_fills
