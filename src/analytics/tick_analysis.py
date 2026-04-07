"""Tick-level analysis functions for deep strategy diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from analytics.metrics import compute_returns, max_drawdown, sharpe_ratio
from sim.limits import get_limit

if TYPE_CHECKING:
    from experiments.models import RunData


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ProductPnL:
    """Per-product PnL attribution."""

    product: str
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    pnl_series: list[float] = field(default_factory=list)
    max_drawdown: float = 0.0
    sharpe: float = 0.0


@dataclass
class PositionLimitIncident:
    """A tick where position was at the limit for a product."""

    timestamp: int
    product: str
    position_at_tick: int
    direction: str  # "long_limit" or "short_limit"


@dataclass
class DrawdownPeriod:
    """A contiguous drawdown period in the PnL curve."""

    start_timestamp: int
    trough_timestamp: int
    end_timestamp: int | None  # None if not recovered by end of data
    peak_pnl: float
    trough_pnl: float
    magnitude: float  # peak - trough (always positive)
    duration_ticks: int


@dataclass
class TickAnalysis:
    """Complete tick-level analysis result."""

    per_product_pnl: dict[str, ProductPnL]
    position_limit_incidents: list[PositionLimitIncident]
    drawdown_periods: list[DrawdownPeriod]  # sorted by magnitude desc
    worst_drawdown: DrawdownPeriod | None


# ---------------------------------------------------------------------------
# Per-product PnL
# ---------------------------------------------------------------------------


def compute_per_product_pnl(run_data: RunData) -> dict[str, ProductPnL]:
    """Compute per-product PnL attribution from RunData.

    Tracks cumulative cash from fills per product, plus unrealized PnL
    from the final position valued at the last mid price.
    """
    # Group fills by product
    product_fills: dict[str, list[tuple[int, int, int]]] = {}  # (timestamp, price, qty)
    for fill in run_data.fills:
        product_fills.setdefault(fill.symbol, []).append(
            (fill.timestamp, fill.price, fill.quantity)
        )

    # Build per-product PnL series tick by tick
    products: set[str] = set()
    for pos_dict in run_data.position_series:
        products.update(pos_dict.keys())
    for fill in run_data.fills:
        products.add(fill.symbol)

    result: dict[str, ProductPnL] = {}

    for product in sorted(products):
        # Compute realized PnL from fills: cash change = -price * quantity
        # (buying costs money, selling earns money)
        cash = 0.0
        fills_by_tick: dict[int, float] = {}
        for ts, price, qty in product_fills.get(product, []):
            delta = -price * qty
            cash += delta
            fills_by_tick[ts] = fills_by_tick.get(ts, 0.0) + delta

        realized_pnl = cash

        # Build per-tick PnL series (cash + unrealized)
        running_cash = 0.0
        pnl_series: list[float] = []
        for i, ts in enumerate(run_data.timestamps):
            running_cash += fills_by_tick.get(ts, 0.0)
            pos = run_data.position_series[i].get(product, 0)
            mid = run_data.mid_price_series[i].get(product, 0.0)
            unrealized = pos * mid
            pnl_series.append(running_cash + unrealized)

        # Final unrealized
        final_pos = run_data.final_positions.get(product, 0)
        last_mid = 0.0
        if run_data.mid_price_series:
            last_mid = run_data.mid_price_series[-1].get(product, 0.0)
        unrealized_pnl = final_pos * last_mid

        total = realized_pnl + unrealized_pnl

        # Compute product-level Sharpe and drawdown
        returns = compute_returns(pnl_series)
        product_sharpe = sharpe_ratio(returns)
        product_dd = max_drawdown(pnl_series)

        result[product] = ProductPnL(
            product=product,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total,
            pnl_series=pnl_series,
            max_drawdown=product_dd,
            sharpe=product_sharpe,
        )

    return result


# ---------------------------------------------------------------------------
# Position limit incidents
# ---------------------------------------------------------------------------


def find_position_limit_incidents(
    run_data: RunData,
) -> list[PositionLimitIncident]:
    """Find ticks where a product's position was at the limit.

    Detects ticks where ``abs(position) >= limit`` for any product.
    """
    incidents: list[PositionLimitIncident] = []
    seen: set[tuple[int, str]] = set()  # (timestamp, product) to deduplicate

    for i, ts in enumerate(run_data.timestamps):
        for product, pos in run_data.position_series[i].items():
            limit = get_limit(product)
            if abs(pos) >= limit and (ts, product) not in seen:
                seen.add((ts, product))
                incidents.append(
                    PositionLimitIncident(
                        timestamp=ts,
                        product=product,
                        position_at_tick=pos,
                        direction="long_limit" if pos > 0 else "short_limit",
                    )
                )

    return incidents


# ---------------------------------------------------------------------------
# Drawdown periods
# ---------------------------------------------------------------------------


def find_drawdown_periods(
    pnl_series: list[float],
    timestamps: list[int],
    min_magnitude: float = 0.0,
) -> list[DrawdownPeriod]:
    """Find all drawdown periods in a PnL series.

    A drawdown starts when PnL drops below a previous peak and ends
    when PnL recovers to that peak (or end of data).

    Returns periods sorted by magnitude descending.
    """
    if len(pnl_series) < 2:
        return []

    periods: list[DrawdownPeriod] = []
    peak = pnl_series[0]
    peak_idx = 0
    trough = pnl_series[0]
    trough_idx = 0
    in_drawdown = False

    for i in range(1, len(pnl_series)):
        val = pnl_series[i]

        if val >= peak:
            # Recovery or new peak
            if in_drawdown:
                magnitude = peak - trough
                if magnitude >= min_magnitude:
                    periods.append(
                        DrawdownPeriod(
                            start_timestamp=timestamps[peak_idx],
                            trough_timestamp=timestamps[trough_idx],
                            end_timestamp=timestamps[i],
                            peak_pnl=peak,
                            trough_pnl=trough,
                            magnitude=magnitude,
                            duration_ticks=trough_idx - peak_idx,
                        )
                    )
                in_drawdown = False
            peak = val
            peak_idx = i
            trough = val
            trough_idx = i
        else:
            in_drawdown = True
            if val < trough:
                trough = val
                trough_idx = i

    # Handle drawdown that extends to end of data
    if in_drawdown:
        magnitude = peak - trough
        if magnitude >= min_magnitude:
            periods.append(
                DrawdownPeriod(
                    start_timestamp=timestamps[peak_idx],
                    trough_timestamp=timestamps[trough_idx],
                    end_timestamp=None,
                    peak_pnl=peak,
                    trough_pnl=trough,
                    magnitude=magnitude,
                    duration_ticks=trough_idx - peak_idx,
                )
            )

    periods.sort(key=lambda p: p.magnitude, reverse=True)
    return periods


# ---------------------------------------------------------------------------
# Combined analysis
# ---------------------------------------------------------------------------


def full_tick_analysis(run_data: RunData) -> TickAnalysis:
    """Run all tick-level analysis and return a combined result."""
    per_product = compute_per_product_pnl(run_data)
    incidents = find_position_limit_incidents(run_data)
    drawdowns = find_drawdown_periods(run_data.pnl_series, run_data.timestamps)

    return TickAnalysis(
        per_product_pnl=per_product,
        position_limit_incidents=incidents,
        drawdown_periods=drawdowns,
        worst_drawdown=drawdowns[0] if drawdowns else None,
    )
