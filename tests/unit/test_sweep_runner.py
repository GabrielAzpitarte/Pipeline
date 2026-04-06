"""Tests for experiments/sweep_runner.py."""

from __future__ import annotations

from pathlib import Path

from experiments.config import ExperimentConfig
from experiments.sweep_runner import run_sweep
from sim.engine import SimConfig


def _make_sweep_config(sweep: dict[str, list[object]] | None = None) -> ExperimentConfig:
    """Create a minimal ExperimentConfig for sweep testing."""
    raw: dict[str, object] = {
        "experiment": {"name": "sweep_test", "strategy": "noop"},
        "data": {
            "prices": "tests/fixtures/sample_prices.csv",
            "trades": "tests/fixtures/sample_trades.csv",
        },
    }
    if sweep is not None:
        raw["sweep"] = sweep

    return ExperimentConfig(
        name="sweep_test",
        strategy="noop",
        dataset_description="test",
        tags=["test"],
        prices_path=Path("tests/fixtures/sample_prices.csv"),
        trades_path=Path("tests/fixtures/sample_trades.csv"),
        sim_config=SimConfig(strategy_name="noop"),
        strategy_params={},
        raw=raw,
    )


class TestRunSweep:
    def test_single_combo(self, tmp_path: Path) -> None:
        cfg = _make_sweep_config(sweep={"x": [1]})
        results = run_sweep(cfg, save=False, artifacts_dir=tmp_path)
        assert len(results) == 1

    def test_grid_count(self, tmp_path: Path) -> None:
        cfg = _make_sweep_config(sweep={"a": [1, 2], "b": [10, 20, 30]})
        results = run_sweep(cfg, save=False, artifacts_dir=tmp_path)
        assert len(results) == 6  # 2 x 3

    def test_unique_run_ids(self, tmp_path: Path) -> None:
        cfg = _make_sweep_config(sweep={"x": [1, 2, 3]})
        results = run_sweep(cfg, save=False, artifacts_dir=tmp_path)
        ids = [r.run_id for r in results]
        assert len(set(ids)) == 3

    def test_sweep_tags(self, tmp_path: Path) -> None:
        cfg = _make_sweep_config(sweep={"x": [1]})
        results = run_sweep(cfg, save=True, artifacts_dir=tmp_path)
        assert "sweep" in results[0].run_data.metadata.tags  # type: ignore[union-attr]

    def test_no_sweep_uses_params(self, tmp_path: Path) -> None:
        cfg = _make_sweep_config()
        results = run_sweep(cfg, save=False, artifacts_dir=tmp_path)
        assert len(results) == 1  # single run with empty params
