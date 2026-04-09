"""Generate structured strategist briefings from market intelligence.

Converts computed stats into concise, actionable asset memos that
help LLM strategists propose better trading architectures.
"""

from __future__ import annotations

from analytics.market_intel import AssetIntelligence


def _classify_spread(avg: float) -> str:
    """Classify spread as tight/moderate/wide."""
    if avg <= 8:
        return "tight"
    if avg <= 16:
        return "moderate"
    return "wide"


def _classify_volatility(vol: float) -> str:
    """Classify volatility."""
    if vol < 1.0:
        return "very low"
    if vol < 3.0:
        return "low"
    if vol < 8.0:
        return "moderate"
    return "high"


def _classify_reversion(ac1: float) -> str:
    """Classify mean reversion from autocorrelation."""
    if ac1 < -0.15:
        return "strong mean reversion"
    if ac1 < -0.05:
        return "mild mean reversion"
    if ac1 > 0.15:
        return "trending"
    if ac1 > 0.05:
        return "mildly trending"
    return "random walk"


def generate_asset_briefing(intel: AssetIntelligence) -> str:
    """Convert computed stats into a structured strategist memo.

    Target: ~600-800 tokens per asset. Organized into facts + angles + traps.
    """
    ms = intel.market_structure
    tf = intel.trade_flow
    pd = intel.price_dynamics
    fo = intel.fill_opportunity
    ir = intel.inventory_risk
    cd = intel.cross_day

    spread_class = _classify_spread(ms.avg_spread)
    vol_class = _classify_volatility(pd.volatility)
    rev_class = _classify_reversion(pd.return_autocorr_1)

    # Determine if stationary or drifting
    is_stationary = abs(pd.drift_per_1000_ticks) < 2.0 and pd.price_range < 50

    lines: list[str] = []
    lines.append(f"## {intel.symbol}")
    lines.append("")

    # Market structure
    lines.append(
        f"**Market structure**: {spread_class} spread ({ms.avg_spread:.0f} avg, "
        f"{ms.spread_std:.1f} std), "
        f"depth {ms.avg_bid_depth:.0f} bid / {ms.avg_ask_depth:.0f} ask, "
        f"book imbalance {ms.avg_book_imbalance:+.2f}, "
        f"thin book {ms.thin_book_rate:.0%} of ticks"
    )

    # Trade flow
    lines.append(
        f"**Trade flow**: {tf.trades_per_tick:.2f} trades/tick, "
        f"avg size {tf.avg_trade_size:.1f}, "
        f"no-trade ticks {tf.no_trade_ticks_rate:.0%}, "
        f"buy aggressor {tf.buy_aggressor_rate:.0%}"
    )

    # Price dynamics
    if is_stationary:
        lines.append(
            f"**Price**: STATIONARY (fair value ~{pd.avg_mid_price:.0f}), "
            f"{vol_class} volatility (sigma={pd.volatility:.2f}), "
            f"{rev_class} (autocorr={pd.return_autocorr_1:.3f}), "
            f"range {pd.price_range:.0f}"
        )
    else:
        lines.append(
            f"**Price**: DRIFTING ({pd.drift_per_1000_ticks:+.1f}/1K ticks), "
            f"{vol_class} volatility (sigma={pd.volatility:.2f}), "
            f"{rev_class} (autocorr={pd.return_autocorr_1:.3f}), "
            f"range {pd.price_range:.0f}"
        )

    # Fill opportunity
    markout_sign = "favorable" if fo.edge_1_markout > 0 else "adverse"
    lines.append(
        f"**Fills**: penny touch rate {fo.penny_touch_rate:.1%}/tick, "
        f"markout after 5 ticks: {fo.edge_1_markout:+.2f} ({markout_sign}), "
        f"adverse selection {fo.adverse_selection_1:.0%}, "
        f"taker opportunities {fo.taker_opportunity_rate:.1%}/tick "
        f"(avg edge {fo.avg_taker_edge:.1f})"
    )

    # Inventory risk
    lines.append(
        f"**Inventory**: naive maker hits limit {ir.naive_limit_hit_rate:.1f}x/10K ticks, "
        f"recovery ~{ir.avg_recovery_ticks:.0f} ticks, "
        f"unwind depth {ir.unwind_opportunity_per_tick:.0f}/tick"
    )

    # Cross-day stability
    if cd.stable_features:
        lines.append(f"**Stability**: STABLE: {', '.join(cd.stable_features)}")
    if cd.variable_features:
        lines.append(f"**Stability**: VARIABLE: {', '.join(cd.variable_features)}")

    # Strategic angles
    lines.append("")
    lines.append("**Strategic angles**:")

    if fo.penny_touch_rate > 0.02 and fo.edge_1_markout > 0:
        lines.append("- Pennying (bb+1/ba-1) is profitable: decent fill rate + positive markout")
    elif fo.penny_touch_rate > 0.02:
        lines.append("- Pennying gets fills but markout is negative — consider wider quotes")
    else:
        lines.append("- Penny fill rate is low — aggressive/taker strategies may be better")

    if is_stationary:
        lines.append(
            f"- Fixed fair value at {pd.avg_mid_price:.0f} — no need for dynamic estimation"
        )
    else:
        lines.append("- Need dynamic fair value (EMA/microprice) — price drifts significantly")

    if pd.mean_reversion_strength > 0.05:
        lines.append("- Mean-reverting: fading large moves is profitable")

    if fo.taker_opportunity_rate > 0.01:
        lines.append(
            f"- Taker opportunities exist ({fo.taker_opportunity_rate:.1%}/tick, "
            f"avg edge {fo.avg_taker_edge:.1f}) — sniping mispriced orders works"
        )

    if tf.no_trade_ticks_rate < 0.3:
        lines.append("- Active market: many ticks have trades, passive fills likely")
    else:
        lines.append(
            f"- Quiet market: {tf.no_trade_ticks_rate:.0%} of ticks have no trades — "
            "passive orders may sit unfilled"
        )

    # Failure modes
    lines.append("")
    lines.append("**Failure modes**:")

    if fo.adverse_selection_1 > 0.5:
        lines.append(
            f"- High adverse selection ({fo.adverse_selection_1:.0%}) — "
            "fills tend to be followed by price moving against you"
        )

    if ir.naive_limit_hit_rate > 5:
        lines.append(
            f"- Inventory trap: naive maker hits limit {ir.naive_limit_hit_rate:.0f}x — "
            "need aggressive unwind logic"
        )

    if ms.thin_book_rate > 0.2:
        lines.append(
            f"- Thin book {ms.thin_book_rate:.0%} of time — large orders will move the market"
        )

    if not is_stationary:
        lines.append("- Fixed fair value will fail — must track drift")

    return "\n".join(lines)


def generate_full_briefing(all_intel: dict[str, AssetIntelligence]) -> str:
    """Generate complete briefing for all assets.

    Returns a structured text block (~1500-2000 tokens total) suitable
    for inclusion in the strategist ideation prompt.
    """
    parts: list[str] = []
    parts.append("# Asset Intelligence Briefing")
    parts.append("*Computed from historical data. Facts, not guesses.*")
    parts.append("")

    for sym in sorted(all_intel.keys()):
        intel = all_intel[sym]
        parts.append(generate_asset_briefing(intel))
        parts.append("")

    return "\n".join(parts)
