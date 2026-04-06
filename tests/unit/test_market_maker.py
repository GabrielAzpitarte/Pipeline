"""Tests for the naive market maker strategy."""

from __future__ import annotations

from trader.datamodel import Listing, Observation, OrderDepth, TradingState
from trader.strategies import STRATEGIES
from trader.strategies.market_maker import MarketMakerStrategy


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


class TestMarketMaker:
    def test_is_registered(self) -> None:
        assert "market_maker" in STRATEGIES

    def test_default_params(self) -> None:
        strat = MarketMakerStrategy()
        assert strat.spread == 4
        assert strat.order_size == 5

    def test_quotes_both_sides(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"RESIN": depth})
        strat = MarketMakerStrategy()
        orders = strat.compute_orders(state)
        assert len(orders["RESIN"]) == 2
        buy, sell = orders["RESIN"]
        assert buy.price == 9998  # int(10000) - 4//2
        assert buy.quantity == 5
        assert sell.price == 10002  # int(10000) + 4//2
        assert sell.quantity == -5

    def test_custom_spread(self) -> None:
        depth = _make_depth({9998: 10}, {10002: 10})
        state = _make_state({"A": depth})
        strat = MarketMakerStrategy(params={"spread": 10, "order_size": 3})
        orders = strat.compute_orders(state)
        buy, sell = orders["A"]
        assert buy.price == 9995  # int(10000) - 10//2
        assert sell.price == 10005

    def test_skips_empty_depth(self) -> None:
        state = _make_state({"A": OrderDepth()})
        strat = MarketMakerStrategy()
        orders = strat.compute_orders(state)
        assert "A" not in orders

    def test_multiple_products(self) -> None:
        d1 = _make_depth({9998: 10}, {10002: 10})
        d2 = _make_depth({2050: 20}, {2054: 20})
        state = _make_state({"A": d1, "B": d2})
        strat = MarketMakerStrategy()
        orders = strat.compute_orders(state)
        assert "A" in orders
        assert "B" in orders
