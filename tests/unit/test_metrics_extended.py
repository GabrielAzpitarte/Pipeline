"""Tests for extended analytics/metrics.py functions."""

from __future__ import annotations

from analytics.metrics import (
    compute_all_metrics,
    compute_returns,
    fill_summary,
    per_product_metrics,
    top_timestamps,
)
from tests.conftest import make_test_run_data


class TestComputeReturns:
    def test_first_differences(self) -> None:
        result = compute_returns([0.0, 10.0, 8.0, 15.0])
        assert result == [10.0, -2.0, 7.0]

    def test_single_value(self) -> None:
        assert compute_returns([5.0]) == []

    def test_empty(self) -> None:
        assert compute_returns([]) == []


class TestComputeAllMetrics:
    def test_has_expected_keys(self) -> None:
        rd = make_test_run_data()
        metrics = compute_all_metrics(rd)
        expected_keys = {
            "total_pnl",
            "final_cash",
            "sharpe",
            "max_drawdown",
            "total_fills",
            "total_buy_fills",
            "total_sell_fills",
            "total_volume",
            "max_position",
            "min_position",
        }
        assert set(metrics.keys()) == expected_keys

    def test_fill_counts(self) -> None:
        rd = make_test_run_data(n_fills=3, products=["A"])
        metrics = compute_all_metrics(rd)
        assert metrics["total_fills"] == 3


class TestPerProductMetrics:
    def test_multi_product(self) -> None:
        rd = make_test_run_data(products=["X", "Y"], n_fills=2)
        ppm = per_product_metrics(rd)
        assert "X" in ppm
        assert "Y" in ppm
        assert ppm["X"]["fill_count"] >= 1
        assert ppm["Y"]["fill_count"] >= 1


class TestTopTimestamps:
    def test_best(self) -> None:
        rd = make_test_run_data(n_ticks=5)
        tops = top_timestamps(rd, n=2, best=True)
        assert len(tops) <= 2
        # Should be sorted by gain descending
        if len(tops) == 2:
            assert tops[0][1] >= tops[1][1]

    def test_worst(self) -> None:
        rd = make_test_run_data(n_ticks=5)
        bottoms = top_timestamps(rd, n=2, best=False)
        assert len(bottoms) <= 2
        if len(bottoms) == 2:
            assert bottoms[0][1] <= bottoms[1][1]


class TestFillSummary:
    def test_basic(self) -> None:
        rd = make_test_run_data(n_fills=2, products=["A"])
        summary = fill_summary(rd.fills)
        assert summary["count"] == 2
        assert summary["volume"] > 0
        assert "A" in summary["products"]

    def test_empty(self) -> None:
        summary = fill_summary([])
        assert summary["count"] == 0
