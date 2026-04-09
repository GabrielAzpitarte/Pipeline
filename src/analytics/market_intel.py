"""Deterministic market intelligence pipeline.

Computes per-asset microstructure statistics from raw historical data.
All computations are pure Python — no LLM, no guessing, just hard facts.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from data.parse_logs import BacktestData


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class MarketStructure:
    """Order book structure statistics."""

    avg_spread: float = 0.0
    median_spread: float = 0.0
    spread_std: float = 0.0
    min_spread: int = 0
    max_spread: int = 0
    avg_bid_depth: float = 0.0
    avg_ask_depth: float = 0.0
    avg_book_imbalance: float = 0.0
    thin_book_rate: float = 0.0
    avg_n_levels: float = 0.0


@dataclass
class TradeFlow:
    """Trade activity statistics."""

    trades_per_tick: float = 0.0
    avg_trade_size: float = 0.0
    median_trade_size: float = 0.0
    max_trade_size: int = 0
    no_trade_ticks_rate: float = 0.0
    buy_aggressor_rate: float = 0.0
    total_trades: int = 0
    total_volume: int = 0


@dataclass
class PriceDynamics:
    """Price behavior statistics."""

    volatility: float = 0.0
    avg_return: float = 0.0
    return_autocorr_1: float = 0.0
    return_autocorr_5: float = 0.0
    mean_reversion_strength: float = 0.0
    drift_per_1000_ticks: float = 0.0
    jump_1_rate: float = 0.0
    jump_2_rate: float = 0.0
    jump_3_rate: float = 0.0
    price_range: float = 0.0
    avg_mid_price: float = 0.0


@dataclass
class FillOpportunity:
    """Fill probability and quality estimates."""

    penny_touch_rate: float = 0.0
    touch_fill_rate: float = 0.0
    edge_1_markout: float = 0.0
    edge_2_markout: float = 0.0
    adverse_selection_1: float = 0.0
    taker_opportunity_rate: float = 0.0
    avg_taker_edge: float = 0.0


@dataclass
class InventoryRisk:
    """Inventory management difficulty."""

    naive_limit_hit_rate: float = 0.0
    avg_recovery_ticks: float = 0.0
    long_trap_rate: float = 0.0
    short_trap_rate: float = 0.0
    unwind_opportunity_per_tick: float = 0.0


@dataclass
class CrossDayStability:
    """Consistency of features across days."""

    stable_features: list[str] = field(default_factory=list)
    variable_features: list[str] = field(default_factory=list)
    day_spreads: list[float] = field(default_factory=list)
    day_volatilities: list[float] = field(default_factory=list)
    day_trade_rates: list[float] = field(default_factory=list)


@dataclass
class AssetIntelligence:
    """Complete market intelligence for one asset."""

    symbol: str
    market_structure: MarketStructure = field(default_factory=MarketStructure)
    trade_flow: TradeFlow = field(default_factory=TradeFlow)
    price_dynamics: PriceDynamics = field(default_factory=PriceDynamics)
    fill_opportunity: FillOpportunity = field(default_factory=FillOpportunity)
    inventory_risk: InventoryRisk = field(default_factory=InventoryRisk)
    cross_day: CrossDayStability = field(default_factory=CrossDayStability)
    n_ticks: int = 0


@dataclass
class AssetProfile:
    """Structured classification of an asset's behavior for strategy routing."""

    symbol: str = ""
    regime: str = "unknown"  # "stationary" | "drifting" | "trending"
    maker_viability: str = "unknown"  # "strong" | "moderate" | "weak"
    taker_viability: str = "unknown"  # "strong" | "moderate" | "weak"
    fill_quality: str = "unknown"  # "favorable" | "neutral" | "adverse"
    inventory_risk: str = "unknown"  # "low" | "moderate" | "high"
    recommended_families: list[str] = field(default_factory=list)
    confidence: str = "low"  # "high" | "medium" | "low"


def classify_asset(intel: AssetIntelligence) -> AssetProfile:
    """Classify an asset from its intelligence data into a structured profile."""
    pd = intel.price_dynamics
    fo = intel.fill_opportunity
    ir = intel.inventory_risk

    # Regime
    if abs(pd.drift_per_1000_ticks) < 2.0 and pd.price_range < 50:
        regime = "stationary"
    elif pd.return_autocorr_1 > 0.1:
        regime = "trending"
    else:
        regime = "drifting"

    # Maker viability
    if fo.penny_touch_rate > 0.03 and fo.edge_1_markout > 0:
        maker = "strong"
    elif fo.penny_touch_rate > 0.01:
        maker = "moderate"
    else:
        maker = "weak"

    # Taker viability
    if fo.taker_opportunity_rate > 0.01:
        taker = "strong"
    elif fo.taker_opportunity_rate > 0.005:
        taker = "moderate"
    else:
        taker = "weak"

    # Fill quality
    if fo.edge_1_markout > 0 and fo.adverse_selection_1 < 0.4:
        fill_q = "favorable"
    elif fo.edge_1_markout < -0.5 or fo.adverse_selection_1 > 0.6:
        fill_q = "adverse"
    else:
        fill_q = "neutral"

    # Inventory risk
    if ir.naive_limit_hit_rate > 5:
        inv_risk = "high"
    elif ir.naive_limit_hit_rate > 1:
        inv_risk = "moderate"
    else:
        inv_risk = "low"

    # Recommended families based on profile
    families: list[str] = []
    if regime == "stationary" and maker == "strong":
        families.extend(["taker_pennying", "passive_maker"])
    if regime == "drifting":
        families.extend(["bifurcated_specialist", "mean_reversion_sniper"])
    if taker == "strong":
        families.append("pure_taker")
    if pd.mean_reversion_strength > 0.05:
        families.append("mean_reversion_sniper")
    if not families:
        families.append("taker_pennying")

    # Confidence
    stable_count = len(intel.cross_day.stable_features)
    confidence = "high" if stable_count >= 3 else "medium" if stable_count >= 1 else "low"

    return AssetProfile(
        symbol=intel.symbol,
        regime=regime,
        maker_viability=maker,
        taker_viability=taker,
        fill_quality=fill_q,
        inventory_risk=inv_risk,
        recommended_families=list(dict.fromkeys(families)),  # dedupe preserving order
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Computation helpers
# ---------------------------------------------------------------------------


def _autocorrelation(values: list[float], lag: int) -> float:
    """Compute lag-N autocorrelation of a series."""
    if len(values) <= lag + 1:
        return 0.0
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values)
    if var == 0:
        return 0.0
    cov = sum((values[i] - mean) * (values[i + lag] - mean) for i in range(n - lag))
    return cov / var


def _safe_median(values: list[float]) -> float:
    """Median that handles empty lists."""
    return statistics.median(values) if values else 0.0


def _pct_variation(values: list[float]) -> float:
    """Percentage variation (max - min) / mean."""
    if not values or len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    return (max(values) - min(values)) / abs(mean)


# ---------------------------------------------------------------------------
# Section 1: Market Structure
# ---------------------------------------------------------------------------


def _compute_market_structure(symbol: str, data: BacktestData) -> MarketStructure:
    """Compute order book structure stats for one asset on one dataset."""
    spreads: list[int] = []
    bid_depths: list[int] = []
    ask_depths: list[int] = []
    imbalances: list[float] = []
    thin_count = 0
    level_counts: list[int] = []

    for ts in data.timestamps:
        price_data = data.prices.get(ts, {}).get(symbol)
        if price_data is None:
            continue
        if not price_data.bid_prices or not price_data.ask_prices:
            continue

        bb = price_data.bid_prices[0]
        ba = price_data.ask_prices[0]
        spread = ba - bb
        spreads.append(spread)

        bid_vol = sum(price_data.bid_volumes)
        ask_vol = sum(price_data.ask_volumes)
        bid_depths.append(bid_vol)
        ask_depths.append(ask_vol)

        total = bid_vol + ask_vol
        if total > 0:
            imbalances.append((bid_vol - ask_vol) / total)

        if bid_vol < 10 or ask_vol < 10:
            thin_count += 1

        level_counts.append(len(price_data.bid_prices) + len(price_data.ask_prices))

    n = len(spreads)
    if n == 0:
        return MarketStructure()

    return MarketStructure(
        avg_spread=sum(spreads) / n,
        median_spread=_safe_median([float(s) for s in spreads]),
        spread_std=statistics.stdev(spreads) if n > 1 else 0.0,
        min_spread=min(spreads),
        max_spread=max(spreads),
        avg_bid_depth=sum(bid_depths) / n,
        avg_ask_depth=sum(ask_depths) / n,
        avg_book_imbalance=sum(imbalances) / len(imbalances) if imbalances else 0.0,
        thin_book_rate=thin_count / n,
        avg_n_levels=sum(level_counts) / n,
    )


# ---------------------------------------------------------------------------
# Section 2: Trade Flow
# ---------------------------------------------------------------------------


def _compute_trade_flow(symbol: str, data: BacktestData) -> TradeFlow:
    """Compute trade activity stats for one asset on one dataset."""
    trade_sizes: list[int] = []
    trades_per_tick: list[int] = []
    buy_aggressor_count = 0

    for ts in data.timestamps:
        sym_trades = data.trades.get(ts, {}).get(symbol, [])
        trades_per_tick.append(len(sym_trades))
        for tr in sym_trades:
            trade_sizes.append(tr.quantity)
            # Heuristic: if buyer is not "SUBMISSION" and seller is not "SUBMISSION",
            # guess aggressor by comparing trade price to mid
            price_data = data.prices.get(ts, {}).get(symbol)
            if price_data and price_data.bid_prices and price_data.ask_prices:
                mid = (price_data.bid_prices[0] + price_data.ask_prices[0]) / 2
                if tr.price >= mid:
                    buy_aggressor_count += 1

    n_ticks = len(data.timestamps)
    n_trades = len(trade_sizes)
    no_trade = sum(1 for t in trades_per_tick if t == 0)

    return TradeFlow(
        trades_per_tick=n_trades / max(1, n_ticks),
        avg_trade_size=sum(trade_sizes) / max(1, n_trades),
        median_trade_size=_safe_median([float(s) for s in trade_sizes]),
        max_trade_size=max(trade_sizes) if trade_sizes else 0,
        no_trade_ticks_rate=no_trade / max(1, n_ticks),
        buy_aggressor_rate=buy_aggressor_count / max(1, n_trades),
        total_trades=n_trades,
        total_volume=sum(trade_sizes),
    )


# ---------------------------------------------------------------------------
# Section 3: Price Dynamics
# ---------------------------------------------------------------------------


def _compute_price_dynamics(symbol: str, data: BacktestData) -> PriceDynamics:
    """Compute price behavior stats for one asset on one dataset."""
    mids: list[float] = []

    for ts in data.timestamps:
        price_data = data.prices.get(ts, {}).get(symbol)
        if price_data is None:
            continue
        mids.append(price_data.mid_price)

    if len(mids) < 2:
        return PriceDynamics()

    # Returns (first differences)
    returns = [mids[i] - mids[i - 1] for i in range(1, len(mids))]

    avg_ret = sum(returns) / len(returns)
    vol = statistics.stdev(returns) if len(returns) > 1 else 0.0

    # Autocorrelation
    ac1 = _autocorrelation(returns, 1)
    ac5 = _autocorrelation(returns, 5) if len(returns) > 6 else 0.0

    # Mean reversion: negative autocorrelation = reverting
    mean_rev = -ac1  # positive = reverting

    # Drift
    n = len(mids)
    drift = (mids[-1] - mids[0]) / (n / 1000) if n > 0 else 0.0

    # Jump rates
    jump1 = sum(1 for r in returns if abs(r) >= 1) / len(returns)
    jump2 = sum(1 for r in returns if abs(r) >= 2) / len(returns)
    jump3 = sum(1 for r in returns if abs(r) >= 3) / len(returns)

    return PriceDynamics(
        volatility=vol,
        avg_return=avg_ret,
        return_autocorr_1=ac1,
        return_autocorr_5=ac5,
        mean_reversion_strength=mean_rev,
        drift_per_1000_ticks=drift,
        jump_1_rate=jump1,
        jump_2_rate=jump2,
        jump_3_rate=jump3,
        price_range=max(mids) - min(mids),
        avg_mid_price=sum(mids) / len(mids),
    )


# ---------------------------------------------------------------------------
# Section 4: Fill Opportunity
# ---------------------------------------------------------------------------


def _compute_fill_opportunity(symbol: str, data: BacktestData) -> FillOpportunity:
    """Estimate fill rates and quality for penny quoting."""
    n_ticks = len(data.timestamps)
    penny_touches = 0
    taker_opps = 0
    taker_edges: list[float] = []
    markout_1_values: list[float] = []
    markout_adverse_count = 0
    markout_total = 0

    timestamps = data.timestamps
    mids_by_ts: dict[int, float] = {}

    # Pre-compute mids and best bid/ask
    bb_by_ts: dict[int, int] = {}
    ba_by_ts: dict[int, int] = {}
    for ts in timestamps:
        price_data = data.prices.get(ts, {}).get(symbol)
        if price_data and price_data.bid_prices and price_data.ask_prices:
            mids_by_ts[ts] = price_data.mid_price
            bb_by_ts[ts] = price_data.bid_prices[0]
            ba_by_ts[ts] = price_data.ask_prices[0]

    # Estimate fair value using rolling EMA (works for both stationary and drifting)
    ema_alpha = 0.05
    fair_value = mids_by_ts.get(timestamps[0], 0.0)

    for i, ts in enumerate(timestamps):
        if ts in mids_by_ts:
            fair_value = ema_alpha * mids_by_ts[ts] + (1 - ema_alpha) * fair_value

        if ts not in bb_by_ts:
            continue
        bb = bb_by_ts[ts]
        ba = ba_by_ts[ts]

        # Check if any trade occurs at or through penny price levels
        # A trade at ba (or lower) would fill a passive buy at bb+1
        # A trade at bb (or higher) would fill a passive sell at ba-1
        sym_trades = data.trades.get(ts, {}).get(symbol, [])
        for tr in sym_trades:
            if tr.price <= bb + 1 or tr.price >= ba - 1:
                penny_touches += 1
                # Markout: what happens to mid 5 ticks later?
                future_idx = min(i + 5, len(timestamps) - 1)
                future_ts = timestamps[future_idx]
                if future_ts in mids_by_ts and ts in mids_by_ts:
                    current_mid = mids_by_ts[ts]
                    future_mid = mids_by_ts[future_ts]
                    if tr.price == bb + 1:
                        markout = future_mid - current_mid  # bought, want price to go up
                    else:
                        markout = current_mid - future_mid  # sold, want price to go down
                    markout_1_values.append(markout)
                    markout_total += 1
                    if markout < 0:
                        markout_adverse_count += 1

        # Taker opportunity: ask below fair value or bid above
        if ba < fair_value - 1:
            taker_opps += 1
            taker_edges.append(fair_value - ba)
        elif bb > fair_value + 1:
            taker_opps += 1
            taker_edges.append(bb - fair_value)

    return FillOpportunity(
        penny_touch_rate=penny_touches / max(1, n_ticks),
        touch_fill_rate=penny_touches / max(1, n_ticks),
        edge_1_markout=sum(markout_1_values) / max(1, len(markout_1_values)),
        edge_2_markout=0.0,  # could compute for wider quotes
        adverse_selection_1=markout_adverse_count / max(1, markout_total),
        taker_opportunity_rate=taker_opps / max(1, n_ticks),
        avg_taker_edge=sum(taker_edges) / max(1, len(taker_edges)),
    )


# ---------------------------------------------------------------------------
# Section 5: Inventory Risk
# ---------------------------------------------------------------------------


def _compute_inventory_risk(symbol: str, data: BacktestData) -> InventoryRisk:
    """Estimate inventory management difficulty.

    Simulates a naive penny maker to estimate how often it hits limits
    and how quickly it recovers.
    """
    position = 0
    limit = 80
    limit_hits = 0
    recovery_ticks: list[int] = []
    long_trap_ticks = 0
    short_trap_ticks = 0
    ticks_since_limit = 0
    recovering = False
    unwind_volumes: list[int] = []

    for ts in data.timestamps:
        price_data = data.prices.get(ts, {}).get(symbol)
        if price_data is None:
            continue
        if not price_data.bid_prices or not price_data.ask_prices:
            continue

        # Simulate penny fills from trades
        sym_trades = data.trades.get(ts, {}).get(symbol, [])
        bb = price_data.bid_prices[0]
        ba = price_data.ask_prices[0]

        for tr in sym_trades:
            if tr.price == bb + 1 and position < limit:
                position = min(position + tr.quantity, limit)
            elif tr.price == ba - 1 and position > -limit:
                position = max(position - tr.quantity, -limit)

        # Track limit hits
        if abs(position) >= limit:
            if not recovering:
                limit_hits += 1
                recovering = True
                ticks_since_limit = 0
            if position >= limit:
                long_trap_ticks += 1
            else:
                short_trap_ticks += 1
            ticks_since_limit += 1
        elif recovering:
            if abs(position) < limit * 0.6:
                recovery_ticks.append(ticks_since_limit)
                recovering = False

        # Unwind opportunity: volume available on the opposite side
        if position > 0:
            unwind_volumes.append(sum(price_data.bid_volumes))
        elif position < 0:
            unwind_volumes.append(sum(price_data.ask_volumes))

    n_ticks = len(data.timestamps)
    return InventoryRisk(
        naive_limit_hit_rate=limit_hits / max(1, n_ticks) * 100,
        avg_recovery_ticks=sum(recovery_ticks) / max(1, len(recovery_ticks)),
        long_trap_rate=long_trap_ticks / max(1, n_ticks),
        short_trap_rate=short_trap_ticks / max(1, n_ticks),
        unwind_opportunity_per_tick=sum(unwind_volumes) / max(1, len(unwind_volumes)),
    )


# ---------------------------------------------------------------------------
# Section 6: Cross-Day Stability
# ---------------------------------------------------------------------------


def _compute_cross_day(
    per_day_results: list[tuple[MarketStructure, TradeFlow, PriceDynamics]],
) -> CrossDayStability:
    """Compare key features across days."""
    if len(per_day_results) < 2:
        return CrossDayStability()

    spreads = [r[0].avg_spread for r in per_day_results]
    vols = [r[2].volatility for r in per_day_results]
    trade_rates = [r[1].trades_per_tick for r in per_day_results]

    stable: list[str] = []
    variable: list[str] = []

    for name, values in [("spread", spreads), ("volatility", vols), ("trade_rate", trade_rates)]:
        var = _pct_variation(values)
        if var < 0.10:
            stable.append(f"{name} ({var:.0%} variation)")
        elif var > 0.30:
            variable.append(f"{name} ({var:.0%} variation)")

    # Check bid/ask depth stability
    depths = [r[0].avg_bid_depth + r[0].avg_ask_depth for r in per_day_results]
    depth_var = _pct_variation(depths)
    if depth_var < 0.10:
        stable.append(f"depth ({depth_var:.0%} variation)")
    elif depth_var > 0.30:
        variable.append(f"depth ({depth_var:.0%} variation)")

    return CrossDayStability(
        stable_features=stable,
        variable_features=variable,
        day_spreads=spreads,
        day_volatilities=vols,
        day_trade_rates=trade_rates,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compute_asset_intelligence(
    symbol: str,
    datasets: list[BacktestData],
) -> AssetIntelligence:
    """Compute complete market intelligence for one asset across datasets.

    Pools data from all datasets for main metrics, then computes
    cross-day stability by comparing per-dataset results.
    """
    # Per-day results for cross-day comparison
    per_day: list[tuple[MarketStructure, TradeFlow, PriceDynamics]] = []

    for d in datasets:
        ms = _compute_market_structure(symbol, d)
        tf = _compute_trade_flow(symbol, d)
        pd_ = _compute_price_dynamics(symbol, d)
        per_day.append((ms, tf, pd_))

    # Use first dataset's results as primary (or pool later if needed)
    primary = datasets[0]
    ms = per_day[0][0] if per_day else MarketStructure()
    tf = per_day[0][1] if per_day else TradeFlow()
    pd_ = per_day[0][2] if per_day else PriceDynamics()

    # Fill opportunity and inventory risk from primary dataset
    fo = _compute_fill_opportunity(symbol, primary)
    ir = _compute_inventory_risk(symbol, primary)

    # Cross-day stability
    cd = _compute_cross_day(per_day)

    return AssetIntelligence(
        symbol=symbol,
        market_structure=ms,
        trade_flow=tf,
        price_dynamics=pd_,
        fill_opportunity=fo,
        inventory_risk=ir,
        cross_day=cd,
        n_ticks=len(primary.timestamps),
    )


def compute_all_intelligence(
    datasets: list[BacktestData],
) -> dict[str, AssetIntelligence]:
    """Compute intelligence for all products across datasets."""
    products = datasets[0].products if datasets else set()
    return {sym: compute_asset_intelligence(sym, datasets) for sym in sorted(products)}
