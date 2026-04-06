"""Regression tests for baseline strategies on sample fixture data.

These tests ensure that baseline strategies:
1. Run without crashing
2. Produce deterministic output
3. Keep positions within limits
4. Produce PnL in a sane range

If any of these fail after a code change, the change likely broke the simulator.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from data.parse_logs import load_round_data
from sim.engine import SimConfig, SimEngine, SimResult

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
PRICES = FIXTURES / "sample_prices.csv"
TRADES = FIXTURES / "sample_trades.csv"


def _run(name: str, params: dict[str, object] | None = None) -> SimResult:
    data = load_round_data(PRICES, TRADES)
    config = SimConfig(strategy_name=name, strategy_params=params or {})
    return SimEngine(config).run(data)


@pytest.mark.regression
class TestMarketMakerRegression:
    def test_no_crash(self) -> None:
        result = _run("market_maker", {"spread": 4, "order_size": 5})
        assert len(result.ticks) == 3

    def test_deterministic(self) -> None:
        r1 = _run("market_maker", {"spread": 4, "order_size": 5})
        r2 = _run("market_maker", {"spread": 4, "order_size": 5})
        assert r1.final_pnl == r2.final_pnl
        assert r1.final_positions == r2.final_positions

    def test_positions_within_limits(self) -> None:
        result = _run("market_maker", {"spread": 4, "order_size": 5})
        for tick in result.ticks:
            for pos in tick.positions.values():
                assert abs(pos) <= 50

    def test_pnl_in_range(self) -> None:
        result = _run("market_maker", {"spread": 4, "order_size": 5})
        assert -10000 < result.final_pnl < 10000


@pytest.mark.regression
class TestFairValueRegression:
    def test_no_crash(self) -> None:
        result = _run("fair_value", {"edge": 2, "order_size": 5})
        assert len(result.ticks) == 3

    def test_deterministic(self) -> None:
        r1 = _run("fair_value", {"edge": 2, "order_size": 5})
        r2 = _run("fair_value", {"edge": 2, "order_size": 5})
        assert r1.final_pnl == r2.final_pnl
        assert r1.final_positions == r2.final_positions

    def test_positions_within_limits(self) -> None:
        result = _run("fair_value", {"edge": 2, "order_size": 5})
        for tick in result.ticks:
            for pos in tick.positions.values():
                assert abs(pos) <= 50

    def test_pnl_in_range(self) -> None:
        result = _run("fair_value", {"edge": 2, "order_size": 5})
        assert -10000 < result.final_pnl < 10000


@pytest.mark.regression
class TestInventoryMMRegression:
    def test_no_crash(self) -> None:
        result = _run("inventory_mm", {"base_spread": 4, "order_size": 5})
        assert len(result.ticks) == 3

    def test_deterministic(self) -> None:
        r1 = _run("inventory_mm", {"base_spread": 4, "order_size": 5})
        r2 = _run("inventory_mm", {"base_spread": 4, "order_size": 5})
        assert r1.final_pnl == r2.final_pnl
        assert r1.final_positions == r2.final_positions

    def test_positions_within_limits(self) -> None:
        result = _run("inventory_mm", {"base_spread": 4, "order_size": 5})
        for tick in result.ticks:
            for pos in tick.positions.values():
                assert abs(pos) <= 50

    def test_pnl_in_range(self) -> None:
        result = _run("inventory_mm", {"base_spread": 4, "order_size": 5})
        assert -10000 < result.final_pnl < 10000
