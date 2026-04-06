"""Tests for the inventory-aware market maker strategy."""

from __future__ import annotations

from trader.datamodel import Listing, Observation, OrderDepth, TradingState
from trader.strategies import STRATEGIES
from trader.strategies.inventory_mm import InventoryMMStrategy


def _make_state(
    depths: dict[str, OrderDepth],
    position: dict[str, int] | None = None,
) -> TradingState:
    listings = {s: Listing(s, s, "SEASHELLS") for s in depths}
    return TradingState(
        timestamp=100,
        traderData="",
        listings=listings,
        order_depths=depths,
        own_trades={},
        market_trades={},
        position=position or {},
        observations=Observation(),
    )


def _make_depth(buys: dict[int, int], sells: dict[int, int]) -> OrderDepth:
    od = OrderDepth()
    od.buy_orders = dict(buys)
    od.sell_orders = {p: -abs(v) for p, v in sells.items()}
    return od


class TestInventoryMM:
    def test_is_registered(self) -> None:
        assert "inventory_mm" in STRATEGIES

    def test_zero_position_no_skew(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"A": depth}, position={"A": 0})
        strat = InventoryMMStrategy(params={"base_spread": 4, "order_size": 5})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        assert buy.price == 9998  # same as market_maker with spread=4
        assert sell.price == 10002

    def test_long_position_skews_down(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"A": depth}, position={"A": 10})
        strat = InventoryMMStrategy(params={"base_spread": 4, "skew_factor": 1.0})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        # skew = 10 * 1.0 = 10. buy = 10000 - 2 - 10 = 9988, sell = 10000 + 2 - 10 = 9992
        assert buy.price == 9988
        assert sell.price == 9992

    def test_short_position_skews_up(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"A": depth}, position={"A": -10})
        strat = InventoryMMStrategy(params={"base_spread": 4, "skew_factor": 1.0})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        # skew = -10 * 1.0 = -10. buy = 10000 - 2 + 10 = 10008, sell = 10000 + 2 + 10 = 10012
        assert buy.price == 10008
        assert sell.price == 10012

    def test_custom_skew_factor(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"A": depth}, position={"A": 10})
        strat = InventoryMMStrategy(params={"base_spread": 4, "skew_factor": 0.5})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        # skew = int(10 * 0.5) = 5. buy = 10000 - 2 - 5 = 9993, sell = 10000 + 2 - 5 = 9997
        assert buy.price == 9993
        assert sell.price == 9997

    def test_skips_empty_depth(self) -> None:
        state = _make_state({"A": OrderDepth()})
        strat = InventoryMMStrategy()
        assert "A" not in strat.compute_orders(state)

    def test_missing_position_defaults_to_zero(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"A": depth})  # no position dict
        strat = InventoryMMStrategy(params={"base_spread": 4})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        assert buy.price == 9998  # no skew
        assert sell.price == 10002
