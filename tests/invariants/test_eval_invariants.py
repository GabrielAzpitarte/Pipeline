"""Evaluation invariant tests — transfer scoring must be consistent."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestTransferScoreDeterminism:
    """Same inputs must produce same transfer score."""

    def test_deterministic_score(self) -> None:
        """Run the same strategy twice, verify identical scores."""
        prices_path = Path("data_raw/prices_round_0_day_-1.csv")
        if not prices_path.exists():
            pytest.skip("Real data not available")

        from data.parse_logs import load_round_data
        from experiments.evaluator import evaluate_candidate

        d1 = load_round_data(prices_path, Path("data_raw/trades_round_0_day_-1.csv"))
        source = Path("src/trader/strategies/microprice_sniper_proven.py").read_text()

        ev1 = evaluate_candidate("test_a", source, {}, [d1])
        ev2 = evaluate_candidate("test_b", source, {}, [d1])

        assert (
            ev1.transfer_score.score == ev2.transfer_score.score
        ), f"Non-deterministic: {ev1.transfer_score.score} != {ev2.transfer_score.score}"
        assert ev1.verdict == ev2.verdict


class TestVerdictConsistency:
    """Verdicts must be logically consistent with metrics."""

    def test_negative_pnl_is_rejected(self) -> None:
        """A strategy with negative PnL across all scenarios should be rejected."""
        from analytics.robustness import FillDiagnostics, MultiScaleMetrics
        from experiments.evaluator import _assign_verdict

        scenario_pnls = {"baseline": -1000.0, "conservative": -2000.0}
        diagnostics = FillDiagnostics()
        multi_scale = MultiScaleMetrics(full_pnl=-1000.0)

        verdict, _notes = _assign_verdict(scenario_pnls, diagnostics, multi_scale)
        assert verdict == "reject"
