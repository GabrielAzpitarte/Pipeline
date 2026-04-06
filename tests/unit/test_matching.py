"""Tests for the two-phase order matching engine (jmerle semantics)."""

from __future__ import annotations

from sim.matching import (
    MarketTrade,
    TradeMatchingMode,
    match_buy_order,
    match_orders,
    match_sell_order,
)
from trader.datamodel import Order, OrderDepth, Trade


def _make_depth(
    buys: dict[int, int] | None = None,
    sells: dict[int, int] | None = None,
) -> OrderDepth:
    """Helper: create an OrderDepth with optional buy/sell sides."""
    od = OrderDepth()
    if buys:
        od.buy_orders = dict(buys)
    if sells:
        od.sell_orders = {p: -abs(v) for p, v in sells.items()}
    return od


def _mt(symbol: str, price: int, qty: int) -> MarketTrade:
    """Helper: create a MarketTrade wrapper."""
    return MarketTrade(
        trade=Trade(symbol, price, qty, "bot_a", "bot_b", 100),
        buy_quantity=qty,
        sell_quantity=qty,
    )


class TestBuyOrderBookMatching:
    def test_full_fill_at_best_ask(self) -> None:
        depth = _make_depth(sells={10002: 10})
        fills = match_buy_order(Order("A", 10002, 5), depth, [])
        assert len(fills) == 1
        assert fills[0].price == 10002
        assert fills[0].quantity == 5
        assert fills[0].against == "book"

    def test_partial_fill_limited_book(self) -> None:
        depth = _make_depth(sells={10002: 3})
        fills = match_buy_order(Order("A", 10002, 5), depth, [])
        assert len(fills) == 1
        assert fills[0].quantity == 3

    def test_multi_level_sweep(self) -> None:
        depth = _make_depth(sells={10002: 10, 10004: 20})
        fills = match_buy_order(Order("A", 10006, 25), depth, [])
        assert len(fills) == 2
        assert fills[0].price == 10002
        assert fills[0].quantity == 10
        assert fills[1].price == 10004
        assert fills[1].quantity == 15

    def test_passive_no_cross(self) -> None:
        depth = _make_depth(sells={10002: 10})
        fills = match_buy_order(Order("A", 10000, 5), depth, [])
        assert fills == []

    def test_empty_book(self) -> None:
        depth = _make_depth()
        fills = match_buy_order(Order("A", 10002, 5), depth, [])
        assert fills == []


class TestSellOrderBookMatching:
    def test_full_fill_at_best_bid(self) -> None:
        depth = _make_depth(buys={9998: 10})
        fills = match_sell_order(Order("A", 9998, -5), depth, [])
        assert len(fills) == 1
        assert fills[0].price == 9998
        assert fills[0].quantity == -5
        assert fills[0].against == "book"

    def test_multi_level_sweep(self) -> None:
        depth = _make_depth(buys={9998: 10, 9996: 20})
        fills = match_sell_order(Order("A", 9994, -25), depth, [])
        assert len(fills) == 2
        assert fills[0].price == 9998
        assert fills[0].quantity == -10
        assert fills[1].price == 9996
        assert fills[1].quantity == -15

    def test_passive_no_cross(self) -> None:
        depth = _make_depth(buys={9998: 10})
        fills = match_sell_order(Order("A", 10000, -5), depth, [])
        assert fills == []


class TestMarketTradeMatching:
    def test_buy_fills_at_order_price(self) -> None:
        """Market trade fills execute at YOUR price, not the trade price."""
        depth = _make_depth()
        mts = [_mt("A", 10001, 10)]
        fills = match_buy_order(Order("A", 10002, 5), depth, mts)
        assert len(fills) == 1
        assert fills[0].price == 10002  # OUR price
        assert fills[0].quantity == 5
        assert fills[0].against == "market_trade"

    def test_sell_fills_at_order_price(self) -> None:
        depth = _make_depth()
        mts = [_mt("A", 9999, 10)]
        fills = match_sell_order(Order("A", 9998, -5), depth, mts)
        assert len(fills) == 1
        assert fills[0].price == 9998

    def test_mode_none_skips_market_trades(self) -> None:
        depth = _make_depth()
        mts = [_mt("A", 10001, 10)]
        fills = match_buy_order(Order("A", 10002, 5), depth, mts, TradeMatchingMode.NONE)
        assert fills == []

    def test_buy_mode_all_skips_above_order_price(self) -> None:
        depth = _make_depth()
        mts = [_mt("A", 10005, 10)]
        fills = match_buy_order(Order("A", 10002, 5), depth, mts, TradeMatchingMode.ALL)
        assert fills == []

    def test_buy_mode_all_matches_at_order_price(self) -> None:
        depth = _make_depth()
        mts = [_mt("A", 10002, 10)]
        fills = match_buy_order(Order("A", 10002, 5), depth, mts, TradeMatchingMode.ALL)
        assert len(fills) == 1
        assert fills[0].quantity == 5

    def test_buy_mode_worse_skips_at_order_price(self) -> None:
        """WORSE mode: trades AT our price are skipped (only strictly better)."""
        depth = _make_depth()
        mts = [_mt("A", 10002, 10)]
        fills = match_buy_order(Order("A", 10002, 5), depth, mts, TradeMatchingMode.WORSE)
        assert fills == []

    def test_buy_mode_worse_matches_below_order_price(self) -> None:
        """WORSE mode: trades BELOW our buy price do match."""
        depth = _make_depth()
        mts = [_mt("A", 10001, 10)]
        fills = match_buy_order(Order("A", 10002, 5), depth, mts, TradeMatchingMode.WORSE)
        assert len(fills) == 1
        assert fills[0].quantity == 5

    def test_sell_mode_worse_skips_at_order_price(self) -> None:
        depth = _make_depth()
        mts = [_mt("A", 9998, 10)]
        fills = match_sell_order(Order("A", 9998, -5), depth, mts, TradeMatchingMode.WORSE)
        assert fills == []

    def test_sell_mode_worse_matches_above_order_price(self) -> None:
        depth = _make_depth()
        mts = [_mt("A", 9999, 10)]
        fills = match_sell_order(Order("A", 9998, -5), depth, mts, TradeMatchingMode.WORSE)
        assert len(fills) == 1


class TestBuySellQuantitySeparation:
    def test_buy_consumes_sell_quantity(self) -> None:
        depth = _make_depth()
        mt = _mt("A", 10001, 10)
        match_buy_order(Order("A", 10002, 5), depth, [mt])
        assert mt.sell_quantity == 5  # consumed 5 from sell side
        assert mt.buy_quantity == 10  # buy side untouched

    def test_sell_consumes_buy_quantity(self) -> None:
        depth = _make_depth()
        mt = _mt("A", 9999, 10)
        match_sell_order(Order("A", 9998, -5), depth, [mt])
        assert mt.buy_quantity == 5
        assert mt.sell_quantity == 10


class TestBookConsumption:
    def test_multiple_orders_consume_book(self) -> None:
        depth = _make_depth(sells={10002: 8})
        orders = {"A": [Order("A", 10002, 5), Order("A", 10002, 5)]}
        fills = match_orders(orders, {"A": depth}, {})
        total_filled = sum(f.quantity for f in fills["A"])
        assert total_filled == 8

    def test_book_level_removed_when_exhausted(self) -> None:
        depth = _make_depth(sells={10002: 5})
        fills = match_buy_order(Order("A", 10002, 5), depth, [])
        assert len(fills) == 1
        assert 10002 not in depth.sell_orders


class TestMatchOrders:
    def test_dispatches_buy_and_sell(self) -> None:
        depth = _make_depth(buys={9998: 10}, sells={10002: 10})
        orders = {"A": [Order("A", 10002, 3), Order("A", 9998, -2)]}
        fills = match_orders(orders, {"A": depth}, {})
        assert len(fills["A"]) == 2
        assert fills["A"][0].quantity == 3
        assert fills["A"][1].quantity == -2

    def test_missing_symbol_no_crash(self) -> None:
        orders = {"UNKNOWN": [Order("UNKNOWN", 100, 5)]}
        fills = match_orders(orders, {}, {})
        assert fills == {}

    def test_zero_quantity_order_ignored(self) -> None:
        depth = _make_depth(sells={100: 10})
        orders = {"A": [Order("A", 100, 0)]}
        fills = match_orders(orders, {"A": depth}, {})
        assert fills == {}
