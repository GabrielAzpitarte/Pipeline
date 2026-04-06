"""Tests for the strategy protocol and registry."""

from __future__ import annotations

from trader.datamodel import Observation, Order, TradingState
from trader.strategies import STRATEGIES, register
from trader.strategies.noop import NoopStrategy


def _make_state() -> TradingState:
    return TradingState(
        timestamp=0,
        traderData="",
        listings={},
        order_depths={},
        own_trades={},
        market_trades={},
        position={},
        observations=Observation(),
    )


class TestNoopStrategy:
    def test_returns_empty_dict(self) -> None:
        strat = NoopStrategy()
        result = strat.compute_orders(_make_state())
        assert result == {}


class TestRegistry:
    def test_noop_is_registered(self) -> None:
        assert "noop" in STRATEGIES
        assert STRATEGIES["noop"] is NoopStrategy

    def test_register_decorator(self) -> None:
        @register("_test_dummy")
        class _DummyStrategy:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {}

        assert "_test_dummy" in STRATEGIES
        assert STRATEGIES["_test_dummy"] is _DummyStrategy
        # Cleanup
        del STRATEGIES["_test_dummy"]

    def test_register_overwrites(self) -> None:
        @register("_test_ow")
        class _First:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {}

        @register("_test_ow")
        class _Second:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {}

        assert STRATEGIES["_test_ow"] is _Second
        del STRATEGIES["_test_ow"]
