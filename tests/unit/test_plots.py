"""Smoke tests for analytics/plots.py — verify plots save without errors."""

from __future__ import annotations

from pathlib import Path

from analytics.plots import (
    plot_dashboard,
    plot_drawdown,
    plot_equity_curve,
    plot_fill_scatter,
    plot_positions,
)
from tests.conftest import make_test_run_data


class TestPlotEquityCurve:
    def test_saves_file(self, tmp_path: Path) -> None:
        out = tmp_path / "equity.png"
        plot_equity_curve([0.0, 10.0, 8.0, 15.0], save_path=out)
        assert out.exists()
        assert out.stat().st_size > 0


class TestPlotPositions:
    def test_saves_file(self, tmp_path: Path) -> None:
        out = tmp_path / "positions.png"
        rd = make_test_run_data()
        plot_positions(rd.timestamps, rd.position_series, save_path=out)
        assert out.exists()
        assert out.stat().st_size > 0


class TestPlotFillScatter:
    def test_saves_file(self, tmp_path: Path) -> None:
        out = tmp_path / "fills.png"
        rd = make_test_run_data()
        plot_fill_scatter(rd.fills, rd.mid_price_series, rd.timestamps, save_path=out)
        assert out.exists()
        assert out.stat().st_size > 0


class TestPlotDrawdown:
    def test_saves_file(self, tmp_path: Path) -> None:
        out = tmp_path / "drawdown.png"
        plot_drawdown([0.0, 10.0, 5.0, 15.0], save_path=out)
        assert out.exists()
        assert out.stat().st_size > 0


class TestPlotDashboard:
    def test_saves_file(self, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.png"
        rd = make_test_run_data()
        plot_dashboard(rd, save_path=out)
        assert out.exists()
        assert out.stat().st_size > 0
