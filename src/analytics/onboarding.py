"""New-round onboarding — diagnose market, classify assets, allocate effort.

When new data arrives, this module automatically profiles each asset,
recommends strategy families, computes opportunity scores, and generates
a complete onboarding package for the orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from agents.prompts.asset_briefing import generate_full_briefing
from analytics.market_intel import (
    AssetIntelligence,
    AssetProfile,
    classify_asset,
    compute_all_intelligence,
)

if TYPE_CHECKING:
    from data.parse_logs import BacktestData


# ---------------------------------------------------------------------------
# Opportunity scoring
# ---------------------------------------------------------------------------


@dataclass
class AssetOpportunity:
    """How much upside remains on this asset."""

    symbol: str
    score: float = 0.0
    current_best_pnl: float = 0.0
    headroom_estimate: float = 0.0
    components: dict[str, float] = field(default_factory=dict)


def compute_opportunity(
    profile: AssetProfile,
    intel: AssetIntelligence,
    current_best_pnl: float = 0.0,
) -> AssetOpportunity:
    """Score the remaining opportunity for one asset.

    Higher score = more room for improvement = deserves more effort.
    """
    components: dict[str, float] = {}
    fo = intel.fill_opportunity

    # Fill quality gap: positive markout not fully exploited
    if fo.edge_1_markout > 0:
        components["fill_quality_upside"] = min(1.0, fo.edge_1_markout * 2)
    else:
        components["fill_quality_upside"] = 0.0

    # Taker opportunity: mispriced orders available
    components["taker_opportunity"] = min(1.0, fo.taker_opportunity_rate * 20)

    # Maker opportunity: penny fills available with good markout
    if fo.penny_touch_rate > 0.02 and fo.edge_1_markout > 0:
        components["maker_opportunity"] = min(1.0, fo.penny_touch_rate * 10)
    else:
        components["maker_opportunity"] = 0.0

    # Mean reversion opportunity
    if intel.price_dynamics.mean_reversion_strength > 0.05:
        components["reversion_opportunity"] = min(
            1.0, intel.price_dynamics.mean_reversion_strength * 5
        )
    else:
        components["reversion_opportunity"] = 0.0

    # Cross-day stability (stable = more confident in opportunity)
    stable_count = len(intel.cross_day.stable_features)
    components["stability_confidence"] = min(1.0, stable_count / 4)

    # Aggregate score
    score = sum(components.values()) / max(1, len(components))

    # Rough headroom estimate
    trade_volume = intel.trade_flow.total_volume
    headroom = trade_volume * 0.01 - current_best_pnl  # rough ceiling

    return AssetOpportunity(
        symbol=intel.symbol,
        score=score,
        current_best_pnl=current_best_pnl,
        headroom_estimate=max(0, headroom),
        components=components,
    )


def allocate_effort(
    opportunities: dict[str, AssetOpportunity],
) -> dict[str, float]:
    """Allocate ideation budget across assets. Returns weight per asset (sum = 1.0).

    High opportunity → more budget. Minimum 20% per asset to avoid
    completely ignoring any product.
    """
    if not opportunities:
        return {}

    n = len(opportunities)
    min_weight = 0.2 / n  # at least 20% total split evenly

    scores = {sym: max(0.01, opp.score) for sym, opp in opportunities.items()}
    total_score = sum(scores.values())

    weights: dict[str, float] = {}
    for sym, score in scores.items():
        raw_weight = score / total_score
        weights[sym] = max(min_weight, raw_weight)

    # Normalize to sum = 1.0
    total = sum(weights.values())
    return {sym: w / total for sym, w in weights.items()}


# ---------------------------------------------------------------------------
# Onboarding pipeline
# ---------------------------------------------------------------------------


@dataclass
class RoundOnboarding:
    """Complete onboarding result for a new round of data."""

    products: list[str]
    intel: dict[str, AssetIntelligence]
    profiles: dict[str, AssetProfile]
    opportunities: dict[str, AssetOpportunity]
    effort_allocation: dict[str, float]
    briefing: str


def onboard_new_round(
    datasets: list[BacktestData],
    best_per_asset: dict[str, float] | None = None,
) -> RoundOnboarding:
    """Diagnose a new round's data and produce a complete onboarding package.

    Args:
        datasets: One or more BacktestData objects (one per day).
        best_per_asset: Current best PnL per asset (for opportunity scoring).
    """
    best_pnl = best_per_asset or {}

    # 1. Compute market intelligence
    intel = compute_all_intelligence(datasets)

    # 2. Classify each asset
    profiles: dict[str, AssetProfile] = {}
    for sym, ai in intel.items():
        profiles[sym] = classify_asset(ai)

    # 3. Compute opportunity scores
    opportunities: dict[str, AssetOpportunity] = {}
    for sym, ai in intel.items():
        opportunities[sym] = compute_opportunity(profiles[sym], ai, best_pnl.get(sym, 0.0))

    # 4. Allocate effort
    effort = allocate_effort(opportunities)

    # 5. Generate briefing
    briefing = generate_full_briefing(intel)

    # Add profile + opportunity info to briefing
    briefing += "\n## Asset Profiles\n"
    for sym in sorted(profiles):
        p = profiles[sym]
        o = opportunities[sym]
        briefing += (
            f"- **{sym}**: regime={p.regime}, maker={p.maker_viability}, "
            f"taker={p.taker_viability}, fill_quality={p.fill_quality}, "
            f"opportunity={o.score:.2f}, effort={effort.get(sym, 0):.0%}\n"
        )
        if p.recommended_families:
            briefing += f"  Recommended families: {', '.join(p.recommended_families)}\n"

    return RoundOnboarding(
        products=sorted(intel.keys()),
        intel=intel,
        profiles=profiles,
        opportunities=opportunities,
        effort_allocation=effort,
        briefing=briefing,
    )
