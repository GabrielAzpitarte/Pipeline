"""Tests for the fair value trader strategy."""

from __future__ import annotations

from trader.datamodel import Listing, Observation, OrderDepth, TradingState
from trader.strategies import STRATEGIES
from trader.strategies.fair_value import FairValueStrategy


def _make_state(depths: dict[str, OrderDepth]) -> TradingState:
    listings = {s: Listing(s, s, "SEASHELLS") for s in depths}
    return TradingState(
        timestamp=100,
        traderData="",
        listings=listings,
        order_depths=depths,
        own_trades={},
        market_trades={},
        position={},
        observations=Observation(),
    )


def _make_depth(buys: dict[int, int], sells: dict[int, int]) -> OrderDepth:
    od = OrderDepth()
    od.buy_orders = dict(buys)
    od.sell_orders = {p: -abs(v) for p, v in sells.items()}
    return od


class TestFairValue:
    def test_is_registered(self) -> None:
        assert "fair_value" in STRATEGIES

    def test_default_params(self) -> None:
        strat = FairValueStrategy()
        assert strat.edge == 2
        assert strat.order_size == 5

    def test_places_orders_at_edge(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"A": depth})
        strat = FairValueStrategy(params={"edge": 2, "order_size": 5})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        assert buy.price == 9998  # int(10000) - 2
        assert sell.price == 10002  # int(10000) + 2

    def test_edge_zero(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"A": depth})
        strat = FairValueStrategy(params={"edge": 0})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        assert buy.price == 10000
        assert sell.price == 10000

    def test_custom_params(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"A": depth})
        strat = FairValueStrategy(params={"edge": 5, "order_size": 10})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        assert buy.price == 9995
        assert sell.price == 10005
        assert buy.quantity == 10
        assert sell.quantity == -10

    def test_skips_empty_depth(self) -> None:
        state = _make_state({"A": OrderDepth()})
        strat = FairValueStrategy()
        assert "A" not in strat.compute_orders(state)

    def test_float_mid_truncated(self) -> None:
        depth = _make_depth({10001: 10}, {10002: 10})  # mid = 10001.5
        state = _make_state({"A": depth})
        strat = FairValueStrategy(params={"edge": 1})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        assert buy.price == 10000  # int(10001.5) - 1 = 10000
        assert sell.price == 10002  # int(10001.5) + 1 = 10002
