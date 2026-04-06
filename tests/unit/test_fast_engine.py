"""Tests for sim/fast_engine.py — fast simulator."""

from __future__ import annotations

from collections import defaultdict

from data.parse_logs import BacktestData, PriceRow
from sim.engine import SimConfig, SimEngine, SimResult
from sim.fast_engine import FastSimEngine, _fast_match_order
from trader.datamodel import Order, OrderDepth


def _make_depth(
    buys: dict[int, int] | None = None,
    sells: dict[int, int] | None = None,
) -> OrderDepth:
    od = OrderDepth()
    if buys:
        od.buy_orders = dict(buys)
    if sells:
        od.sell_orders = {p: -abs(v) for p, v in sells.items()}
    return od


def _simple_data() -> BacktestData:
    return BacktestData(
        timestamps=[100, 200],
        prices={
            100: {
                "A": PriceRow(1, 100, "A", [9998], [10], [10002], [10], 10000.0, 0.0),
            },
            200: {
                "A": PriceRow(1, 200, "A", [9999], [12], [10001], [12], 10000.0, 0.0),
            },
        },
        trades=defaultdict(dict),
        products={"A"},
    )


class TestFastMatchOrder:
    def test_buy_crosses_ask(self) -> None:
        depth = _make_depth(sells={10002: 10})
        fill = _fast_match_order(Order("A", 10002, 5), depth)
        assert fill is not None
        assert fill.price == 10002
        assert fill.quantity == 5

    def test_buy_below_ask_no_fill(self) -> None:
        depth = _make_depth(sells={10002: 10})
        fill = _fast_match_order(Order("A", 10000, 5), depth)
        assert fill is None

    def test_sell_crosses_bid(self) -> None:
        depth = _make_depth(buys={9998: 10})
        fill = _fast_match_order(Order("A", 9998, -5), depth)
        assert fill is not None
        assert fill.price == 9998
        assert fill.quantity == -5

    def test_sell_above_bid_no_fill(self) -> None:
        depth = _make_depth(buys={9998: 10})
        fill = _fast_match_order(Order("A", 10000, -5), depth)
        assert fill is None

    def test_empty_book_no_fill(self) -> None:
        fill = _fast_match_order(Order("A", 10000, 5), OrderDepth())
        assert fill is None

    def test_partial_fill_capped(self) -> None:
        depth = _make_depth(sells={10002: 3})
        fill = _fast_match_order(Order("A", 10002, 10), depth)
        assert fill is not None
        assert fill.quantity == 3

    def test_book_not_mutated(self) -> None:
        depth = _make_depth(sells={10002: 10})
        _fast_match_order(Order("A", 10002, 5), depth)
        assert depth.sell_orders[10002] == -10  # unchanged


class TestFastSimEngine:
    def test_noop_zero_pnl(self) -> None:
        data = _simple_data()
        engine = FastSimEngine(SimConfig(strategy_name="noop"))
        result = engine.run(data)
        assert isinstance(result, SimResult)
        assert result.final_pnl == 0.0
        assert result.all_fills == []
        assert len(result.ticks) == 2

    def test_produces_sim_result(self) -> None:
        data = _simple_data()
        engine = FastSimEngine(SimConfig(strategy_name="noop"))
        result = engine.run(data)
        assert isinstance(result, SimResult)
        for tick in result.ticks:
            assert hasattr(tick, "timestamp")
            assert hasattr(tick, "pnl")

    def test_no_market_trade_fills(self) -> None:
        data = _simple_data()
        engine = FastSimEngine(SimConfig(strategy_name="noop"))
        result = engine.run(data)
        for fill in result.all_fills:
            assert fill.against != "market_trade"


class TestFastVsFaithful:
    def test_noop_identical(self) -> None:
        data = _simple_data()
        faithful = SimEngine(SimConfig(strategy_name="noop")).run(data)
        fast = FastSimEngine(SimConfig(strategy_name="noop")).run(data)
        assert faithful.final_pnl == fast.final_pnl
        assert faithful.final_positions == fast.final_positions
        assert faithful.final_cash == fast.final_cash
