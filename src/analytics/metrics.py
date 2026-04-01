"""Performance metrics for strategy evaluation."""

from __future__ import annotations

import math


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
