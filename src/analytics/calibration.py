"""Platform calibration layer using known submission results.

Uses historical platform PnL data to assess whether the transfer score
correlates better with platform outcomes than raw backtest PnL.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CalibrationPoint:
    """One known backtest → platform result pair."""

    strategy_name: str
    backtest_pnl: float
    platform_pnl: float
    transfer_score: float | None = None


# Known calibration data from historical submissions
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


def spearman_rank_correlation(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation between two lists.

    Returns a value in [-1, 1]. Higher = better rank agreement.
    """
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
    """Evaluate how well backtest PnL and transfer score predict platform PnL.

    Returns dict with:
      - raw_pnl_correlation: Spearman(backtest_pnl, platform_pnl)
      - transfer_score_correlation: Spearman(transfer_score, platform_pnl)
      - improvement: transfer - raw (positive = new system is better)
    """
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
