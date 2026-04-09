"""Platform calibration layer — evidence collection from known submissions.

Every platform-tested strategy becomes a structured evidence point with
full local diagnostics for future calibration modeling.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CalibrationPoint:
    """One known backtest -> platform result pair with full diagnostics."""

    strategy_name: str
    backtest_pnl: float
    platform_pnl: float
    transfer_score: float | None = None
    verdict: str | None = None
    architecture_family: str | None = None
    scenario_pnls: dict[str, float] = field(default_factory=dict)
    per_asset_pnl: dict[str, float] = field(default_factory=dict)
    passive_fill_share: float | None = None
    avg_markout: float | None = None
    submission_reason: str | None = None
    date_submitted: str | None = None
    strategy_code_hash: str | None = None


# Hardcoded known results (legacy — will be supplemented by calibration_data.json)
KNOWN_RESULTS: list[CalibrationPoint] = [
    CalibrationPoint("market_maker", 5446, 970),
    CalibrationPoint("strat1_simple_penny", 10836, 1450),
    CalibrationPoint("strat3_vol_adaptive", 6245, 1080),
    CalibrationPoint("microprice_sniper_proven", 15503, 2517),
    CalibrationPoint("strat4_taker_penny", 14908, 2540),
    CalibrationPoint("strat5_skewed_taker_penny", 15396, 2400),
    CalibrationPoint("strat6_hybrid_asset_specialist", 14920, 1520),
    CalibrationPoint("strat7_assembled_best", 15000, 2520),
    CalibrationPoint("strat8_liquidity_momentum", 15003, 2490),
    CalibrationPoint("nonlinear_skew_v1", 15897, 1800),
    CalibrationPoint("vol_adaptive_dual_ema_v1", 4191, 900),
    CalibrationPoint("bifurcated_em_taker_tom_micro_v3", 15179, 2500),
    CalibrationPoint("bifurcated_em_taker_tom_micro_v2", 15147, 2539),
    CalibrationPoint("assembled_best_per_asset", 15000, 2500),
]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_calibration(points: list[CalibrationPoint], path: Path) -> None:
    """Save calibration data to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(p) for p in points]
    path.write_text(json.dumps(data, indent=2, default=str))


def load_calibration(path: Path) -> list[CalibrationPoint]:
    """Load calibration data from JSON, falling back to KNOWN_RESULTS."""
    if not path.exists():
        return list(KNOWN_RESULTS)
    raw: list[dict[str, Any]] = json.loads(path.read_text())
    points: list[CalibrationPoint] = []
    for d in raw:
        points.append(
            CalibrationPoint(
                strategy_name=d["strategy_name"],
                backtest_pnl=d["backtest_pnl"],
                platform_pnl=d["platform_pnl"],
                transfer_score=d.get("transfer_score"),
                verdict=d.get("verdict"),
                architecture_family=d.get("architecture_family"),
                scenario_pnls=d.get("scenario_pnls", {}),
                per_asset_pnl=d.get("per_asset_pnl", {}),
                passive_fill_share=d.get("passive_fill_share"),
                avg_markout=d.get("avg_markout"),
                submission_reason=d.get("submission_reason"),
                date_submitted=d.get("date_submitted"),
                strategy_code_hash=d.get("strategy_code_hash"),
            )
        )
    return points


def add_calibration_point(point: CalibrationPoint, path: Path) -> None:
    """Add a calibration point to the persisted dataset."""
    points = load_calibration(path)
    # Upsert by name
    for i, p in enumerate(points):
        if p.strategy_name == point.strategy_name:
            points[i] = point
            save_calibration(points, path)
            return
    points.append(point)
    save_calibration(points, path)


# ---------------------------------------------------------------------------
# Ranking quality
# ---------------------------------------------------------------------------


def spearman_rank_correlation(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation between two lists."""
    if len(x) != len(y) or len(x) < 2:
        return 0.0

    n = len(x)

    def _ranks(values: list[float]) -> list[float]:
        indexed = sorted(enumerate(values), key=lambda iv: iv[1])
        ranks = [0.0] * n
        for rank, (orig_idx, _) in enumerate(indexed):
            ranks[orig_idx] = float(rank)
        return ranks

    rx = _ranks(x)
    ry = _ranks(y)
    d_sq = sum((a - b) ** 2 for a, b in zip(rx, ry, strict=True))
    return 1.0 - (6.0 * d_sq) / (n * (n**2 - 1))


def evaluate_ranking_quality(
    points: list[CalibrationPoint],
) -> dict[str, float]:
    """Evaluate how well backtest PnL and transfer score predict platform PnL."""
    backtests = [p.backtest_pnl for p in points]
    platform = [p.platform_pnl for p in points]

    raw_corr = spearman_rank_correlation(backtests, platform)
    result: dict[str, float] = {"raw_pnl_correlation": raw_corr}

    scored_points = [p for p in points if p.transfer_score is not None]
    if len(scored_points) >= 2:
        ts_values = [p.transfer_score for p in scored_points]  # type: ignore[misc]
        ts_platform = [p.platform_pnl for p in scored_points]
        ts_corr = spearman_rank_correlation(ts_values, ts_platform)
        result["transfer_score_correlation"] = ts_corr
        result["improvement"] = ts_corr - raw_corr

    return result


def evaluate_calibration_quality(
    points: list[CalibrationPoint],
) -> dict[str, float]:
    """Assess calibration model quality across all evidence.

    Returns metrics on prediction accuracy and rank agreement.
    """
    if len(points) < 3:
        return {"n_points": float(len(points)), "sufficient_data": 0.0}

    # Compute prediction errors using leave-one-out ratio method
    errors: list[float] = []
    for i, p in enumerate(points):
        if p.backtest_pnl <= 0 or p.platform_pnl <= 0:
            continue
        # Use all other points to predict this one
        others = [
            q for j, q in enumerate(points) if j != i and q.backtest_pnl > 0 and q.platform_pnl > 0
        ]
        if not others:
            continue
        avg_ratio = sum(q.backtest_pnl / q.platform_pnl for q in others) / len(others)
        predicted = p.backtest_pnl / avg_ratio
        errors.append(abs(predicted - p.platform_pnl))

    mae = sum(errors) / len(errors) if errors else 0.0
    mape = (
        sum(
            e / max(1, p.platform_pnl)
            for e, p in zip(errors, points, strict=False)
            if p.platform_pnl > 0
        )
        / max(1, len(errors))
        * 100
    )

    # Family-wise accuracy
    families: dict[str, list[float]] = {}
    for p in points:
        if p.architecture_family and p.platform_pnl > 0 and p.backtest_pnl > 0:
            families.setdefault(p.architecture_family, []).append(p.backtest_pnl / p.platform_pnl)

    family_consistency = {}
    for fam, ratios in families.items():
        if len(ratios) >= 2:
            mean_r = sum(ratios) / len(ratios)
            std_r = (sum((r - mean_r) ** 2 for r in ratios) / (len(ratios) - 1)) ** 0.5
            family_consistency[fam] = std_r / mean_r if mean_r > 0 else 1.0

    return {
        "n_points": float(len(points)),
        "sufficient_data": 1.0 if len(points) >= 8 else 0.0,
        "mean_absolute_error": mae,
        "mean_absolute_pct_error": mape,
        "n_families_with_data": float(len(family_consistency)),
        "avg_family_ratio_cv": sum(family_consistency.values()) / max(1, len(family_consistency)),
    }
