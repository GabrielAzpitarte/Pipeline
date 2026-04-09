"""Tests for experiments/artifacts.py — canonical run artifact."""

from __future__ import annotations

from experiments.artifacts import (
    RunArtifact,
    StoredFill,
    artifact_to_dict,
    compute_per_asset,
    compute_summary,
    dict_to_artifact,
    finalize_artifact,
    validate_artifact,
)


def _make_artifact(n_ticks: int = 5) -> RunArtifact:
    """Create a minimal valid artifact for testing."""
    timestamps = list(range(100, 100 + n_ticks * 100, 100))
    fills = [
        StoredFill(timestamp=100, symbol="EMERALDS", price=10000, quantity=5, against="book"),
        StoredFill(
            timestamp=200, symbol="EMERALDS", price=10001, quantity=-5, against="market_trade"
        ),
        StoredFill(
            timestamp=100, symbol="TOMATOES", price=5000, quantity=3, against="market_trade"
        ),
    ]
    pnl = [0.0, 5.0, 10.0, 8.0, 12.0][:n_ticks]
    cash = [0.0, -50000.0, 50.0, 50.0, 50.0][:n_ticks]
    positions = [
        {"EMERALDS": 5, "TOMATOES": 3},
        {"EMERALDS": 0, "TOMATOES": 3},
        {"EMERALDS": 0, "TOMATOES": 3},
        {"EMERALDS": 0, "TOMATOES": 3},
        {"EMERALDS": 0, "TOMATOES": 3},
    ][:n_ticks]
    mids = [
        {"EMERALDS": 10000.0, "TOMATOES": 5000.0},
        {"EMERALDS": 10001.0, "TOMATOES": 5001.0},
        {"EMERALDS": 10000.0, "TOMATOES": 5002.0},
        {"EMERALDS": 10000.0, "TOMATOES": 5001.0},
        {"EMERALDS": 10001.0, "TOMATOES": 5003.0},
    ][:n_ticks]

    return RunArtifact(
        run_id="test_001",
        strategy_name="test_strat",
        timestamp="2026-04-09T00:00:00",
        dataset_id="day_-1",
        scenario_name="baseline",
        tick_timestamps=timestamps,
        pnl_path=pnl,
        cash_path=cash,
        positions_path=positions,
        mid_prices_path=mids,
        fills=fills,
        orders_submitted=[{} for _ in timestamps],
    )


class TestRunArtifactSchema:
    def test_create_minimal(self) -> None:
        a = RunArtifact(run_id="x", strategy_name="y")
        assert a.run_id == "x"
        assert a.summary.final_pnl == 0.0

    def test_finalize_computes_summary(self) -> None:
        a = _make_artifact()
        a = finalize_artifact(a)
        assert a.summary.total_fills == 3
        assert a.summary.passive_fills == 2
        assert a.summary.aggressive_fills == 1

    def test_finalize_computes_per_asset(self) -> None:
        a = _make_artifact()
        a = finalize_artifact(a)
        assert "EMERALDS" in a.per_asset
        assert "TOMATOES" in a.per_asset
        assert a.per_asset["EMERALDS"].fills == 2
        assert a.per_asset["TOMATOES"].fills == 1


class TestComputeSummary:
    def test_fill_counts(self) -> None:
        a = _make_artifact()
        s = compute_summary(a)
        assert s.total_fills == 3
        assert s.passive_fills == 2
        assert s.passive_fill_share > 0.5

    def test_pnl(self) -> None:
        a = _make_artifact()
        s = compute_summary(a)
        assert s.final_pnl == a.pnl_path[-1]


class TestComputePerAsset:
    def test_both_assets_present(self) -> None:
        a = _make_artifact()
        pa = compute_per_asset(a)
        assert "EMERALDS" in pa
        assert "TOMATOES" in pa

    def test_fill_split(self) -> None:
        a = _make_artifact()
        pa = compute_per_asset(a)
        assert pa["EMERALDS"].aggressive_fills == 1
        assert pa["EMERALDS"].passive_fills == 1
        assert pa["TOMATOES"].passive_fills == 1


class TestSerialization:
    def test_roundtrip(self) -> None:
        a = _make_artifact()
        a = finalize_artifact(a)
        d = artifact_to_dict(a)
        b = dict_to_artifact(d)
        assert b.run_id == a.run_id
        assert b.summary.total_fills == a.summary.total_fills
        assert len(b.fills) == len(a.fills)
        assert b.per_asset.keys() == a.per_asset.keys()

    def test_json_serializable(self) -> None:
        import json

        a = _make_artifact()
        a = finalize_artifact(a)
        d = artifact_to_dict(a)
        text = json.dumps(d, default=str)
        assert len(text) > 100


class TestValidation:
    def test_valid_artifact_passes(self) -> None:
        a = _make_artifact()
        a = finalize_artifact(a)
        errors = validate_artifact(a)
        assert len(errors) == 0

    def test_mismatched_lengths_caught(self) -> None:
        a = _make_artifact()
        a.pnl_path = a.pnl_path[:3]  # truncate
        errors = validate_artifact(a)
        assert any("pnl_path length" in e for e in errors)

    def test_missing_run_id_caught(self) -> None:
        a = _make_artifact()
        a.run_id = ""
        errors = validate_artifact(a)
        assert any("Missing run_id" in e for e in errors)
