"""Compare results across experiment runs."""

from __future__ import annotations

from typing import Any


def compare_runs(
    runs: list[dict[str, Any]],
    metric: str = "total_pnl",
) -> list[dict[str, Any]]:
    """Sort runs by a given metric, best first."""
    return sorted(runs, key=lambda r: r.get(metric, 0), reverse=True)
