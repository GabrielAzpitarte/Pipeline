"""Disciplined platform-testing policy.

Controls when and what to submit, predicts outcomes, and ingests results
back into the evidence pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analytics.calibration import (
    CalibrationPoint,
    add_calibration_point,
    load_calibration,
    predict_platform_pnl,
)
from trader.logging_utils import get_logger

_log = get_logger("submission.policy")


@dataclass
class SubmissionCandidate:
    """A strategy recommended for platform testing."""

    strategy_name: str
    strategy_code: str
    local_prediction: float
    confidence: str  # "high" | "medium" | "low"
    submission_reason: str  # "local_winner" | "new_family" | "calibration" | "diversity"
    architecture_family: str
    transfer_score: float
    verdict: str
    backtest_pnl: float = 0.0


# PlatformPrediction and predict_platform_pnl are now in analytics.calibration
# (canonical prediction interface — imported above)


def rank_candidates_for_platform(
    candidates: list[SubmissionCandidate],
    calibration_data: list[CalibrationPoint],
    tested_families: set[str] | None = None,
) -> list[SubmissionCandidate]:
    """Rank candidates by calibration-aware score, not raw transfer score.

    Score = lower_bound * diversity_bonus * (1 - uncertainty_penalty) + transfer_weight
    """
    tested = tested_families or {
        p.architecture_family for p in calibration_data if p.architecture_family
    }
    scored: list[tuple[float, SubmissionCandidate]] = []

    for c in candidates:
        pred = predict_platform_pnl(c.backtest_pnl, calibration_data, c.architecture_family)

        # Base: conservative lower bound
        base = pred.lower_bound

        # Diversity bonus: untested family gets 20% boost
        diversity = 1.2 if c.architecture_family not in tested else 1.0

        # Uncertainty penalty
        penalty = 0.0
        if pred.confidence == "low":
            penalty = 0.1
        if pred.out_of_distribution:
            penalty = 0.2

        # Transfer weight: partial credit for local robustness
        transfer_bonus = c.transfer_score * 500  # scale to PnL-like magnitude

        score = base * diversity * (1 - penalty) + transfer_bonus
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def should_submit(
    candidate: SubmissionCandidate,
    history: list[CalibrationPoint],
    budget_remaining: int = 5,
    tested_families: set[str] | None = None,
) -> tuple[bool, str]:
    """Decide whether to submit a candidate for platform testing.

    Returns:
        (should_submit, reason)
    """
    if budget_remaining <= 0:
        return False, "No budget remaining"

    if candidate.verdict in ("reject", "simulator_artifact"):
        return False, f"Verdict is {candidate.verdict} — not worth testing"

    tested = tested_families or set()

    # Reason 1: New architecture family not yet tested
    if candidate.architecture_family not in tested:
        return True, f"New family: {candidate.architecture_family} not yet platform-tested"

    # Reason 2: Significantly better than existing calibration
    best_platform = max((p.platform_pnl for p in history), default=0)
    if candidate.local_prediction > best_platform * 1.1:
        return (
            True,
            f"Predicted {candidate.local_prediction:.0f} > 110% of best ({best_platform:.0f})",
        )

    # Reason 3: Low budget but high-confidence candidate
    if budget_remaining <= 2 and candidate.confidence == "high":
        return True, "Final selection — high-confidence candidate"

    # Reason 4: Diversity — verdict is robust (rare)
    if candidate.verdict == "robust":
        return True, "Rare robust verdict — worth validating"

    return False, "Does not meet submission criteria"


def ingest_platform_result(
    strategy_name: str,
    platform_pnl: float,
    local_prediction: float,
    backtest_pnl: float,
    architecture_family: str,
    transfer_score: float,
    memory: Any,
    calibration_path: Path,
) -> dict[str, Any]:
    """Process a platform result and update all evidence systems.

    Updates strategy card, adds calibration point, computes prediction error.
    """
    # 1. Update strategy card
    for card in memory._cards:
        if card.get("name") == strategy_name:
            card["platform_tested"] = True
            card["platform_pnl"] = platform_pnl
            card["confidence"] = "platform_proven"
            if platform_pnl > 2000:
                card["strengths"] = (
                    card.get("strengths", "") + f" PLATFORM PROVEN {platform_pnl:.0f} PnL."
                ).strip()
            break
    memory._save_cards()

    # 2. Add calibration point
    point = CalibrationPoint(
        strategy_name=strategy_name,
        backtest_pnl=backtest_pnl,
        platform_pnl=platform_pnl,
        transfer_score=transfer_score,
        architecture_family=architecture_family,
        submission_reason="pipeline",
    )
    add_calibration_point(point, calibration_path)

    # 3. Compute prediction error
    error = platform_pnl - local_prediction
    error_pct = error / max(1, abs(local_prediction)) * 100

    # 4. Classify discrepancy
    if abs(error_pct) < 15:
        discrepancy = "accurate"
    elif error > 0:
        discrepancy = "underestimate"
    else:
        discrepancy = "overestimate"

    summary = {
        "strategy_name": strategy_name,
        "platform_pnl": platform_pnl,
        "local_prediction": local_prediction,
        "error": error,
        "error_pct": error_pct,
        "discrepancy": discrepancy,
    }

    _log.info(
        "Platform result ingested: %s — platform=%d, predicted=%d, error=%+d (%.0f%%, %s)",
        strategy_name,
        platform_pnl,
        local_prediction,
        error,
        error_pct,
        discrepancy,
    )

    return summary


def recommend_for_platform(
    memory: Any,
    calibration_path: Path,
    budget: int = 3,
) -> list[SubmissionCandidate]:
    """Recommend strategies for platform testing based on policy.

    Returns up to `budget` candidates, prioritizing diversity and novelty.
    """
    calibration = load_calibration(calibration_path)
    tested_families = {p.architecture_family for p in calibration if p.architecture_family}

    candidates: list[SubmissionCandidate] = []

    for card in sorted(
        memory._cards,
        key=lambda c: c.get("transfer_score", 0),
        reverse=True,
    ):
        if card.get("platform_tested") or card.get("status") == "failed":
            continue
        if not card.get("code"):
            continue

        pnl = card.get("pnl", 0)
        family = card.get("architecture_family", "unknown")
        ts = card.get("transfer_score", 0)
        verdict = card.get("verdict", "unknown")

        pred = predict_platform_pnl(pnl, calibration, family)

        sc = SubmissionCandidate(
            strategy_name=card["name"],
            strategy_code=card["code"],
            local_prediction=pred.predicted_pnl,
            confidence=pred.confidence,
            submission_reason="",
            architecture_family=family,
            transfer_score=ts,
            verdict=verdict,
            backtest_pnl=pnl,
        )

        should, reason = should_submit(sc, calibration, budget - len(candidates), tested_families)
        if should:
            sc.submission_reason = reason
            candidates.append(sc)
            tested_families.add(family)  # prevent double-submitting same family

        if len(candidates) >= budget:
            break

    return candidates
