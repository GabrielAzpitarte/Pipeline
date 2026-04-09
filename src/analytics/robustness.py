"""Robustness metrics, transfer diagnostics, and transfer score.

This module evaluates how well a strategy's backtest performance will
transfer to the real platform by measuring:
- Multi-scale PnL stability (2K-tick blocks matching platform length)
- Fill source breakdown (passive vs aggressive)
- Scenario robustness (baseline vs conservative)
- Cross-day consistency
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Multi-scale evaluation (Step 6)
# ---------------------------------------------------------------------------


@dataclass
class BlockResult:
    """PnL result for one contiguous block of ticks."""

    block_index: int
    start_tick: int
    end_tick: int
    pnl: float
    fills: int


@dataclass
class MultiScaleMetrics:
    """Multi-horizon robustness metrics."""

    full_pnl: float
    block_pnls: list[float] = field(default_factory=list)
    median_block_pnl: float = 0.0
    min_block_pnl: float = 0.0
    lower_quantile_pnl: float = 0.0  # 25th percentile
    positive_block_rate: float = 0.0
    block_pnl_std: float = 0.0
    cross_day_pnls: list[float] = field(default_factory=list)
    cross_day_spread: float = 0.0
    cross_day_consistency: float = 0.0  # min/max ratio


def compute_multi_scale(
    pnl_series: list[float],
    block_size: int = 2000,
) -> MultiScaleMetrics:
    """Split a PnL series into blocks and compute robustness metrics.

    Each block's PnL is the difference between end and start of that block.
    Block size defaults to 2000 to match the platform's ~2K tick test length.
    """
    if not pnl_series:
        return MultiScaleMetrics(full_pnl=0.0)

    full_pnl = pnl_series[-1]
    n = len(pnl_series)

    # Split into contiguous blocks
    block_pnls: list[float] = []
    for start in range(0, n, block_size):
        end = min(start + block_size, n)
        if end - start < block_size // 2:
            break  # skip tiny trailing block
        start_pnl = pnl_series[start - 1] if start > 0 else 0.0
        end_pnl = pnl_series[end - 1]
        block_pnls.append(end_pnl - start_pnl)

    if not block_pnls:
        return MultiScaleMetrics(full_pnl=full_pnl)

    sorted_pnls = sorted(block_pnls)
    n_blocks = len(sorted_pnls)
    median_idx = n_blocks // 2
    q25_idx = max(0, n_blocks // 4)

    mean_bp = sum(block_pnls) / n_blocks
    variance = sum((p - mean_bp) ** 2 for p in block_pnls) / max(1, n_blocks - 1)
    positive_count = sum(1 for p in block_pnls if p > 0)

    return MultiScaleMetrics(
        full_pnl=full_pnl,
        block_pnls=block_pnls,
        median_block_pnl=sorted_pnls[median_idx],
        min_block_pnl=sorted_pnls[0],
        lower_quantile_pnl=sorted_pnls[q25_idx],
        positive_block_rate=positive_count / n_blocks,
        block_pnl_std=math.sqrt(variance),
    )


def add_cross_day_info(
    metrics: MultiScaleMetrics,
    cross_day_pnls: list[float],
) -> MultiScaleMetrics:
    """Attach cross-day consistency info to multi-scale metrics."""
    if not cross_day_pnls:
        return metrics
    max_pnl = max(cross_day_pnls)
    min_pnl = min(cross_day_pnls)
    metrics.cross_day_pnls = cross_day_pnls
    metrics.cross_day_spread = max_pnl - min_pnl
    metrics.cross_day_consistency = min_pnl / max_pnl if max_pnl > 0 else 0.0
    return metrics


# ---------------------------------------------------------------------------
# Fill diagnostics (Step 7)
# ---------------------------------------------------------------------------


@dataclass
class FillDiagnostics:
    """Execution quality diagnostics — passive vs aggressive, markouts, edge."""

    total_fills: int = 0
    passive_fills: int = 0
    aggressive_fills: int = 0
    passive_fill_share: float = 0.0
    passive_pnl_share: float = 0.0
    avg_inventory: float = 0.0
    max_inventory: int = 0
    turnover: float = 0.0
    avg_markout_5: float = 0.0
    adverse_rate_5: float = 0.0
    avg_edge: float = 0.0
    inventory_half_life: float = 0.0


def compute_fill_diagnostics(metrics: dict[str, float]) -> FillDiagnostics:
    """Build FillDiagnostics from sweep worker metrics dict."""
    total = int(metrics.get("total_fills", 0))
    passive = int(metrics.get("passive_fills", 0))
    aggressive = int(metrics.get("aggressive_fills", 0))
    return FillDiagnostics(
        total_fills=total,
        passive_fills=passive,
        aggressive_fills=aggressive,
        passive_fill_share=metrics.get("passive_fill_share", 0.0),
        passive_pnl_share=0.0,
        avg_inventory=metrics.get("avg_inventory", 0.0),
        max_inventory=int(metrics.get("max_inventory", 0)),
        turnover=metrics.get("turnover", 0.0),
        avg_markout_5=metrics.get("avg_markout_5", 0.0),
        adverse_rate_5=metrics.get("adverse_rate_5", 0.0),
        avg_edge=metrics.get("avg_edge", 0.0),
        inventory_half_life=metrics.get("inventory_half_life", 0.0),
    )


# ---------------------------------------------------------------------------
# Transfer score (Step 8)
# ---------------------------------------------------------------------------

# Default weights — configurable
DEFAULT_WEIGHTS: dict[str, float] = {
    "median_block_pnl": 0.30,
    "min_block_pnl": 0.20,
    "full_pnl": 0.15,
    "conservative_pnl": 0.10,
    "positive_block_rate": 0.05,
    "cross_day_consistency": 0.05,
    "scenario_gap_penalty": -0.05,
    "passive_dependency_penalty": -0.05,
    "inventory_penalty": -0.03,
    "cross_day_penalty": -0.02,
}


@dataclass
class TransferScore:
    """Transfer-aware score with component breakdown."""

    score: float
    components: dict[str, float] = field(default_factory=dict)


def compute_transfer_score(
    multi_scale: MultiScaleMetrics,
    diagnostics: FillDiagnostics,
    scenario_pnls: dict[str, float] | None = None,
    weights: dict[str, float] | None = None,
    normalization_maxes: dict[str, float] | None = None,
) -> TransferScore:
    """Compute a platform-transfer-aware score.

    Args:
        multi_scale: Block-level and cross-day metrics.
        diagnostics: Fill source breakdown.
        scenario_pnls: PnL under each scenario (e.g. {"baseline": 15000, "conservative": 12000}).
        weights: Override default component weights.
        normalization_maxes: Max values for normalization (e.g. from full sweep).
            If None, raw values are used (useful for single-candidate scoring).
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    nmax = normalization_maxes or {}

    def _norm(val: float, key: str) -> float:
        """Normalize a value to [0, 1] using the max from the sweep."""
        mx = nmax.get(key)
        if mx and mx > 0:
            return val / mx
        return val / 10000.0  # fallback normalization

    components: dict[str, float] = {}

    # Rewards
    components["median_block_pnl"] = _norm(multi_scale.median_block_pnl, "median_block_pnl")
    components["min_block_pnl"] = _norm(multi_scale.min_block_pnl, "min_block_pnl")
    components["full_pnl"] = _norm(multi_scale.full_pnl, "full_pnl")
    components["positive_block_rate"] = multi_scale.positive_block_rate
    components["cross_day_consistency"] = multi_scale.cross_day_consistency

    # Conservative scenario
    scenario_pnls = scenario_pnls or {}
    baseline_pnl = scenario_pnls.get("baseline", multi_scale.full_pnl)
    conservative_pnl = scenario_pnls.get("conservative", baseline_pnl)
    components["conservative_pnl"] = _norm(conservative_pnl, "conservative_pnl")

    # Penalties (all in [0, 1] range, higher = worse)
    if baseline_pnl > 0:
        components["scenario_gap_penalty"] = (baseline_pnl - conservative_pnl) / baseline_pnl
    else:
        components["scenario_gap_penalty"] = 0.0

    components["passive_dependency_penalty"] = (
        diagnostics.passive_fill_share * diagnostics.passive_fill_share
    )

    components["inventory_penalty"] = min(1.0, diagnostics.avg_inventory / 50.0)

    mean_cd = (
        sum(multi_scale.cross_day_pnls) / len(multi_scale.cross_day_pnls)
        if multi_scale.cross_day_pnls
        else 1.0
    )
    components["cross_day_penalty"] = (
        multi_scale.cross_day_spread / abs(mean_cd) if mean_cd != 0 else 0.0
    )

    # Compute weighted score
    score = 0.0
    for key, weight in w.items():
        val = components.get(key, 0.0)
        score += weight * val

    return TransferScore(score=score, components=components)


def compute_normalization_maxes(
    all_multi_scale: list[MultiScaleMetrics],
    all_scenario_pnls: list[dict[str, float]],
) -> dict[str, float]:
    """Compute max values across all candidates for normalization."""
    maxes: dict[str, float] = {
        "median_block_pnl": 1.0,
        "min_block_pnl": 1.0,
        "full_pnl": 1.0,
        "conservative_pnl": 1.0,
    }
    for ms in all_multi_scale:
        maxes["median_block_pnl"] = max(maxes["median_block_pnl"], abs(ms.median_block_pnl))
        maxes["min_block_pnl"] = max(maxes["min_block_pnl"], abs(ms.min_block_pnl))
        maxes["full_pnl"] = max(maxes["full_pnl"], abs(ms.full_pnl))
    for sp in all_scenario_pnls:
        maxes["conservative_pnl"] = max(maxes["conservative_pnl"], abs(sp.get("conservative", 0.0)))
    return maxes


# ---------------------------------------------------------------------------
# Portfolio score (from per-asset scores)
# ---------------------------------------------------------------------------


def compute_portfolio_score(
    asset_scores: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Compute portfolio-level score from per-asset scores.

    Default: equal weight across assets. Adds a penalty if one asset
    contributes more than 80% of the total score (over-reliance risk).
    """
    if not asset_scores:
        return 0.0
    w = weights or {s: 1.0 / len(asset_scores) for s in asset_scores}
    base = sum(w.get(s, 0) * score for s, score in asset_scores.items())

    # Penalty for imbalance
    total = sum(abs(v) for v in asset_scores.values())
    if total > 0:
        max_share = max(abs(v) for v in asset_scores.values()) / total
        if max_share > 0.8:
            base *= 0.9  # 10% penalty for over-reliance on one asset

    return base
