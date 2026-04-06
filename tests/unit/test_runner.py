"""Tests for experiments/runner.py."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from data.parse_logs import BacktestData, PriceRow
from experiments.runner import run_experiment


def _simple_data() -> BacktestData:
    return BacktestData(
        timestamps=[100, 200],
        prices={
            100: {"A": PriceRow(1, 100, "A", [9998], [10], [10002], [10], 10000.0, 0.0)},
            200: {"A": PriceRow(1, 200, "A", [9999], [12], [10001], [12], 10000.0, 0.0)},
        },
        trades=defaultdict(dict),
        products={"A"},
    )


class TestRunExperiment:
    def test_noop_runs(self, tmp_path: Path) -> None:
        result = run_experiment(
            name="test_noop",
            strategy="noop",
            data=_simple_data(),
            save=True,
            artifacts_dir=tmp_path,
        )
        assert result.run_id != ""
        assert result.run_data is not None
        assert result.metrics["total_pnl"] == 0.0

    def test_saves_to_disk(self, tmp_path: Path) -> None:
        result = run_experiment(
            name="test_save",
            strategy="noop",
            data=_simple_data(),
            save=True,
            artifacts_dir=tmp_path,
        )
        assert result.output_dir is not None
        assert (result.output_dir / "result.json").exists()

    def test_no_save(self, tmp_path: Path) -> None:
        result = run_experiment(
            name="test_nosave",
            strategy="noop",
            data=_simple_data(),
            save=False,
            artifacts_dir=tmp_path,
        )
        assert result.output_dir is None
        # No files should exist
        runs_dir = tmp_path / "runs"
        assert not runs_dir.exists() or not any(runs_dir.iterdir())

    def test_metrics_populated(self, tmp_path: Path) -> None:
        result = run_experiment(
            name="test_metrics",
            strategy="noop",
            data=_simple_data(),
            save=False,
            artifacts_dir=tmp_path,
        )
        assert "total_pnl" in result.metrics
        assert "sharpe" in result.metrics
        assert "max_drawdown" in result.metrics
        assert "total_fills" in result.metrics

    def test_fast_flag(self, tmp_path: Path) -> None:
        result = run_experiment(
            name="test_fast",
            strategy="noop",
            data=_simple_data(),
            save=False,
            artifacts_dir=tmp_path,
            fast=True,
        )
        assert result.metrics["total_pnl"] == 0.0
        assert result.run_data is not None

    def test_strategy_params_stored(self, tmp_path: Path) -> None:
        result = run_experiment(
            name="test_params",
            strategy="noop",
            data=_simple_data(),
            strategy_params={"spread": 4},
            save=False,
            artifacts_dir=tmp_path,
        )
        assert result.config["strategy_params"] == {"spread": 4}
