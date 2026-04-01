"""Dashboard generation for experiment review."""

from __future__ import annotations

from typing import Any


def generate_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a summary dict from a list of experiment results."""
    return {
        "num_runs": len(results),
        "best_pnl": max((r.get("total_pnl", 0.0) for r in results), default=0.0),
        "worst_pnl": min((r.get("total_pnl", 0.0) for r in results), default=0.0),
    }
