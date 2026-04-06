"""Compare results across experiment runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from analytics.metrics import compute_all_metrics
from data.storage import load_run


def compare_runs(
    runs: list[dict[str, Any]],
    metric: str = "total_pnl",
) -> list[dict[str, Any]]:
    """Sort runs by a given metric, best first."""
    return sorted(runs, key=lambda r: r.get(metric, 0), reverse=True)


def compare_two_runs(
    run_id_a: str,
    run_id_b: str,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Load two runs and compute comparative metrics.

    Returns dict with run_a metrics, run_b metrics, deltas, and winner.
    """
    run_a = load_run(run_id_a, base_dir=base_dir)
    run_b = load_run(run_id_b, base_dir=base_dir)

    metrics_a = compute_all_metrics(run_a)
    metrics_b = compute_all_metrics(run_b)

    deltas = {k: metrics_b.get(k, 0.0) - metrics_a.get(k, 0.0) for k in metrics_a}

    better = "b" if metrics_b.get("total_pnl", 0.0) >= metrics_a.get("total_pnl", 0.0) else "a"

    return {
        "run_a": {"run_id": run_id_a, "metrics": metrics_a},
        "run_b": {"run_id": run_id_b, "metrics": metrics_b},
        "deltas": deltas,
        "better": better,
    }
