"""Tests for submission/policy.py — platform testing policy."""

from __future__ import annotations

from analytics.calibration import PlatformPrediction, predict_platform_pnl
from submission.policy import (
    SubmissionCandidate,
    rank_candidates_for_platform,
    recommend_for_platform,
)


class TestPolicyImportable:
    def test_functions_callable(self) -> None:
        assert callable(predict_platform_pnl)
        assert callable(recommend_for_platform)
        assert callable(rank_candidates_for_platform)


class TestPredictPlatformPnl:
    def test_returns_prediction_object(self) -> None:
        from analytics.calibration import KNOWN_RESULTS

        pred = predict_platform_pnl(10000, KNOWN_RESULTS)
        assert isinstance(pred, PlatformPrediction)

    def test_bounds_are_ordered(self) -> None:
        from analytics.calibration import KNOWN_RESULTS

        pred = predict_platform_pnl(10000, KNOWN_RESULTS)
        assert pred.lower_bound <= pred.predicted_pnl <= pred.upper_bound

    def test_empty_calibration_returns_fallback(self) -> None:
        pred = predict_platform_pnl(10000, [])
        assert pred.method == "fallback"
        assert pred.confidence == "low"

    def test_ood_detection(self) -> None:
        from analytics.calibration import KNOWN_RESULTS

        # Very high PnL with unknown family should be OOD
        pred = predict_platform_pnl(100000, KNOWN_RESULTS, "totally_new_family")
        assert pred.out_of_distribution


class TestRankCandidates:
    def test_diversity_bonus(self) -> None:
        from analytics.calibration import CalibrationPoint

        cal = [CalibrationPoint("a", 10000, 2000, architecture_family="taker_pennying")]

        c1 = SubmissionCandidate(
            "s1", "", 2000, "medium", "", "taker_pennying", 0.5, "robust", 10000
        )
        c2 = SubmissionCandidate("s2", "", 2000, "medium", "", "pure_taker", 0.5, "robust", 10000)

        ranked = rank_candidates_for_platform([c1, c2], cal, {"taker_pennying"})
        # pure_taker should rank higher (diversity bonus)
        assert ranked[0].architecture_family == "pure_taker"
