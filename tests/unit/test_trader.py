"""Tests for the Trader class."""

from __future__ import annotations

from typing import Any

import pytest

from trader.datamodel import Listing, Observation, Order, OrderDepth, TradingState
from trader.strategies import STRATEGIES, register
from trader.trader import Trader

# ---------------------------------------------------------------------------
# Parameterized strategy for testing params support
# ---------------------------------------------------------------------------

_RECEIVED_PARAMS: dict[str, Any] = {}


def _make_state(
    position: dict[str, int] | None = None,
    trader_data: str = "",
) -> TradingState:
    """Create a minimal TradingState for testing."""
    return TradingState(
        timestamp=100,
        traderData=trader_data,
        listings={"AMETHYSTS": Listing("AMETHYSTS", "AMETHYSTS", "SEASHELLS")},
        order_depths={"AMETHYSTS": OrderDepth()},
        own_trades={},
        market_trades={},
        position=position or {},
        observations=Observation(),
    )


class TestTraderNoop:
    def test_noop_returns_empty(self) -> None:
        trader = Trader("noop")
        orders, conversions, data = trader.run(_make_state())
        assert orders == {}
        assert conversions == 0
        assert data == ""


class TestTraderUnknownStrategy:
    def test_unknown_strategy_raises(self) -> None:
        trader = Trader("nonexistent_strategy_xyz")
        with pytest.raises(ValueError, match="Unknown strategy"):
            trader.run(_make_state())


class TestTraderRiskFiltering:
    def setup_method(self) -> None:
        """Register a test strategy that returns orders testing position limits."""

        @register("_test_risky")
        class _RiskyStrategy:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {
                    "AMETHYSTS": [
                        Order("AMETHYSTS", 10000, 10),  # buy 10, position would be 10
                        Order("AMETHYSTS", 10001, 8),  # buy 8, position would be 18
                        Order("AMETHYSTS", 10002, 5),  # buy 5, position would be 23 > 20
                    ]
                }

    def teardown_method(self) -> None:
        STRATEGIES.pop("_test_risky", None)

    def test_risk_filters_excess_orders(self) -> None:
        trader = Trader("_test_risky")
        orders, _, _ = trader.run(_make_state())
        # pos=0: +10=10 ok, +8=18 ok, +5=23 rejected (limit=20)
        assert len(orders.get("AMETHYSTS", [])) == 2
        assert orders["AMETHYSTS"][0].quantity == 10
        assert orders["AMETHYSTS"][1].quantity == 8

    def test_risk_filters_with_existing_position(self) -> None:
        trader = Trader("_test_risky")
        state = _make_state(position={"AMETHYSTS": 10})
        orders, _, _ = trader.run(state)
        # pos=10: +10=20 ok, +8=28 rejected, +5 never reached
        assert len(orders.get("AMETHYSTS", [])) == 1
        assert orders["AMETHYSTS"][0].quantity == 10


class TestTraderParams:
    def setup_method(self) -> None:
        _RECEIVED_PARAMS.clear()

        @register("_test_parameterized")
        class _ParamStrategy:
            def __init__(self, params: dict[str, Any] | None = None) -> None:
                _RECEIVED_PARAMS.update(params or {})

            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {}

    def teardown_method(self) -> None:
        STRATEGIES.pop("_test_parameterized", None)
        _RECEIVED_PARAMS.clear()

    def test_params_passed_to_strategy(self) -> None:
        trader = Trader("_test_parameterized", params={"spread": 4})
        trader.run(_make_state())
        assert _RECEIVED_PARAMS["spread"] == 4

    def test_noop_ignores_params(self) -> None:
        trader = Trader("noop", params={"spread": 4})
        orders, _, _ = trader.run(_make_state())
        assert orders == {}  # no crash, works fine
