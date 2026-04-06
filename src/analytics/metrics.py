"""Performance metrics for strategy evaluation."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from experiments.models import RunData, StoredFill


def sharpe_ratio(returns: list[float], risk_free: float = 0.0) -> float:
    """Annualised Sharpe ratio from a list of period returns."""
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns) - risk_free
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return mean / std


def max_drawdown(equity_curve: list[float]) -> float:
    """Maximum peak-to-trough drawdown."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        peak = max(peak, val)
        dd = (peak - val) / peak if peak != 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def total_pnl(fills: list[dict[str, float]]) -> float:
    """Sum of PnL across all fills."""
    return sum(f.get("pnl", 0.0) for f in fills)


# ---------------------------------------------------------------------------
# RunData-aware metrics
# ---------------------------------------------------------------------------


def compute_returns(pnl_series: list[float]) -> list[float]:
    """Compute per-tick PnL changes (first differences)."""
    if len(pnl_series) < 2:
        return []
    return [pnl_series[i] - pnl_series[i - 1] for i in range(1, len(pnl_series))]


def compute_all_metrics(run_data: RunData) -> dict[str, float]:
    """Compute a full metrics dictionary from a stored run.

    Keys: total_pnl, final_cash, sharpe, max_drawdown,
          total_fills, total_buy_fills, total_sell_fills,
          total_volume, max_position, min_position.
    """
    returns = compute_returns(run_data.pnl_series)

    buy_fills = [f for f in run_data.fills if f.quantity > 0]
    sell_fills = [f for f in run_data.fills if f.quantity < 0]
    total_volume = sum(abs(f.quantity) for f in run_data.fills)

    # Track max/min positions across all ticks and products
    all_positions: list[int] = []
    for pos_dict in run_data.position_series:
        all_positions.extend(pos_dict.values())

    return {
        "total_pnl": run_data.final_pnl,
        "final_cash": run_data.final_cash,
        "sharpe": sharpe_ratio(returns),
        "max_drawdown": max_drawdown(run_data.pnl_series),
        "total_fills": float(len(run_data.fills)),
        "total_buy_fills": float(len(buy_fills)),
        "total_sell_fills": float(len(sell_fills)),
        "total_volume": float(total_volume),
        "max_position": float(max(all_positions)) if all_positions else 0.0,
        "min_position": float(min(all_positions)) if all_positions else 0.0,
    }


def per_product_metrics(
    run_data: RunData,
) -> dict[str, dict[str, float]]:
    """Compute metrics broken down by product."""
    products: dict[str, list[StoredFill]] = {}
    for fill in run_data.fills:
        products.setdefault(fill.symbol, []).append(fill)

    result: dict[str, dict[str, float]] = {}
    for product, fills_list in products.items():
        buys = [f for f in fills_list if f.quantity > 0]
        sells = [f for f in fills_list if f.quantity < 0]
        result[product] = {
            "fill_count": float(len(fills_list)),
            "buy_count": float(len(buys)),
            "sell_count": float(len(sells)),
            "total_volume": float(sum(abs(f.quantity) for f in fills_list)),
            "avg_buy_price": (
                sum(f.price * f.quantity for f in buys) / sum(f.quantity for f in buys)
                if buys
                else 0.0
            ),
            "avg_sell_price": (
                sum(f.price * abs(f.quantity) for f in sells) / sum(abs(f.quantity) for f in sells)
                if sells
                else 0.0
            ),
            "net_quantity": float(sum(f.quantity for f in fills_list)),
        }
    return result


def top_timestamps(
    run_data: RunData,
    n: int = 5,
    best: bool = True,
) -> list[tuple[int, float]]:
    """Return the N timestamps with the largest PnL gains (or losses).

    Returns list of (timestamp, pnl_change) tuples.
    """
    returns = compute_returns(run_data.pnl_series)
    if not returns:
        return []

    # returns[i] corresponds to timestamps[i+1] (change from tick i to i+1)
    pairs = list(zip(run_data.timestamps[1:], returns, strict=True))
    pairs.sort(key=lambda x: x[1], reverse=best)
    return pairs[:n]


def fill_summary(fills: list[Any]) -> dict[str, Any]:
    """Aggregate fill statistics."""
    if not fills:
        return {"count": 0, "volume": 0, "products": []}

    products: set[str] = set()
    total_volume = 0
    for f in fills:
        products.add(f.symbol)
        total_volume += abs(f.quantity)

    return {
        "count": len(fills),
        "volume": total_volume,
        "products": sorted(products),
    }
