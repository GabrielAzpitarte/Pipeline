"""Tests for analytics/tick_analysis.py."""

from __future__ import annotations

import sys
from pathlib import Path

# conftest.py is in tests/, add it to path for make_test_run_data
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.tick_analysis import (
    compute_per_product_pnl,
    find_drawdown_periods,
    find_position_limit_incidents,
    full_tick_analysis,
)
from conftest import make_test_run_data
from experiments.models import RunData, RunMetadata, StoredFill


def _make_run_data_with_limits() -> RunData:
    """Create RunData where positions hit the limit (80 for EMERALDS)."""
    timestamps = [100, 200, 300, 400, 500]
    fills = [
        StoredFill(timestamp=100, symbol="EMERALDS", price=10000, quantity=40, against="book"),
        StoredFill(timestamp=200, symbol="EMERALDS", price=10001, quantity=40, against="book"),
        # Now at position 80 (the limit)
        StoredFill(timestamp=300, symbol="EMERALDS", price=10002, quantity=-10, against="book"),
        StoredFill(timestamp=400, symbol="EMERALDS", price=10003, quantity=-10, against="book"),
    ]

    positions = [
        {"EMERALDS": 40},
        {"EMERALDS": 80},
        {"EMERALDS": 70},
        {"EMERALDS": 60},
        {"EMERALDS": 60},
    ]
    cash = 0.0
    cash_series = []
    pnl_series = []
    mid_price_series = []
    for i, _ts in enumerate(timestamps):
        mid = 10000.0 + i
        # Approximate cash tracking
        if i == 0:
            cash = -10000 * 40
        elif i == 1:
            cash += -10001 * 40
        elif i == 2:
            cash += 10002 * 10
        elif i == 3:
            cash += 10003 * 10
        cash_series.append(cash)
        unrealized = positions[i]["EMERALDS"] * mid
        pnl_series.append(cash + unrealized)
        mid_price_series.append({"EMERALDS": mid})

    return RunData(
        metadata=RunMetadata(
            run_id="test_limits",
            timestamp="2026-04-01T12:00:00+00:00",
            strategy_name="test",
            config={},
            git_hash="abc",
            dataset_description="test",
            tags=["test"],
        ),
        timestamps=timestamps,
        pnl_series=pnl_series,
        position_series=positions,
        cash_series=cash_series,
        mid_price_series=mid_price_series,
        fills=fills,
        orders_submitted=[{} for _ in timestamps],
        final_pnl=pnl_series[-1],
        final_positions={"EMERALDS": 60},
        final_cash=cash,
    )


class TestComputePerProductPnl:
    def test_single_product(self) -> None:
        rd = make_test_run_data(n_ticks=5, products=["EMERALDS"], n_fills=2)
        result = compute_per_product_pnl(rd)
        assert "EMERALDS" in result
        pp = result["EMERALDS"]
        assert len(pp.pnl_series) == 5

    def test_multi_product(self) -> None:
        rd = make_test_run_data(n_ticks=5, products=["EMERALDS", "TOMATOES"], n_fills=2)
        result = compute_per_product_pnl(rd)
        assert "EMERALDS" in result
        assert "TOMATOES" in result

    def test_pnl_series_length_matches_ticks(self) -> None:
        rd = make_test_run_data(n_ticks=10, products=["EMERALDS"], n_fills=3)
        result = compute_per_product_pnl(rd)
        assert len(result["EMERALDS"].pnl_series) == 10


class TestFindPositionLimitIncidents:
    def test_detects_limit(self) -> None:
        rd = _make_run_data_with_limits()
        incidents = find_position_limit_incidents(rd)
        assert len(incidents) >= 1
        # Position 80 at timestamp 200
        limit_ts = [inc.timestamp for inc in incidents if inc.position_at_tick == 80]
        assert 200 in limit_ts

    def test_correct_direction(self) -> None:
        rd = _make_run_data_with_limits()
        incidents = find_position_limit_incidents(rd)
        for inc in incidents:
            if inc.position_at_tick == 80:
                assert inc.direction == "long_limit"

    def test_no_incidents_below_limit(self) -> None:
        rd = make_test_run_data(n_ticks=5, products=["AMETHYSTS"], n_fills=2)
        incidents = find_position_limit_incidents(rd)
        assert len(incidents) == 0


class TestFindDrawdownPeriods:
    def test_no_drawdown(self) -> None:
        pnl = [1.0, 2.0, 3.0, 4.0, 5.0]
        ts = [100, 200, 300, 400, 500]
        periods = find_drawdown_periods(pnl, ts)
        assert len(periods) == 0

    def test_single_drawdown(self) -> None:
        pnl = [10.0, 8.0, 5.0, 7.0, 11.0]
        ts = [100, 200, 300, 400, 500]
        periods = find_drawdown_periods(pnl, ts)
        assert len(periods) == 1
        assert periods[0].magnitude == 5.0  # 10 - 5
        assert periods[0].trough_timestamp == 300

    def test_unrecovered_drawdown(self) -> None:
        pnl = [10.0, 8.0, 5.0, 6.0, 7.0]
        ts = [100, 200, 300, 400, 500]
        periods = find_drawdown_periods(pnl, ts)
        assert len(periods) == 1
        assert periods[0].end_timestamp is None

    def test_multiple_drawdowns(self) -> None:
        pnl = [10.0, 5.0, 12.0, 8.0, 15.0]
        ts = [100, 200, 300, 400, 500]
        periods = find_drawdown_periods(pnl, ts)
        assert len(periods) == 2
        # Sorted by magnitude desc
        assert periods[0].magnitude >= periods[1].magnitude

    def test_empty_series(self) -> None:
        assert find_drawdown_periods([], []) == []

    def test_single_point(self) -> None:
        assert find_drawdown_periods([10.0], [100]) == []


class TestFullTickAnalysis:
    def test_returns_all_components(self) -> None:
        rd = make_test_run_data(n_ticks=5, products=["EMERALDS", "TOMATOES"], n_fills=2)
        analysis = full_tick_analysis(rd)
        assert len(analysis.per_product_pnl) == 2
        assert isinstance(analysis.position_limit_incidents, list)
        assert isinstance(analysis.drawdown_periods, list)
