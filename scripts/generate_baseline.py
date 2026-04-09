"""Generate the baseline comparison sheet (artifacts/baseline_comparison.json).

Runs each golden baseline strategy through the evaluator and saves
full diagnostics for future comparison.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, ".")


def main() -> None:
    """Generate baseline comparison data."""
    from tests.golden.baseline_package import BASELINE_STRATEGIES

    from data.parse_logs import load_round_data
    from experiments.evaluator import evaluate_candidate

    d1 = load_round_data(
        Path("data_raw/prices_round_0_day_-1.csv"),
        Path("data_raw/trades_round_0_day_-1.csv"),
    )
    d2 = load_round_data(
        Path("data_raw/prices_round_0_day_-2.csv"),
        Path("data_raw/trades_round_0_day_-2.csv"),
    )
    datasets = [d1, d2]

    results: dict[str, dict] = {}

    for name, info in BASELINE_STRATEGIES.items():
        source_path = Path(str(info["source"]))
        if not source_path.exists():
            print(f"SKIP {name}: {source_path} not found")
            continue

        source = source_path.read_text()
        print(f"Evaluating {name}...")

        ev = evaluate_candidate(name, source, {}, datasets)

        results[name] = {
            "category": info.get("category", "unknown"),
            "known_platform_pnl": info.get("known_platform_pnl"),
            "backtest_pnl": ev.raw_pnl,
            "transfer_score": ev.transfer_score.score,
            "transfer_components": ev.transfer_score.components,
            "verdict": ev.verdict,
            "fragility_notes": ev.fragility_notes,
            "fill_diagnostics": {
                "total_fills": ev.fill_diagnostics.total_fills,
                "passive_fill_share": ev.fill_diagnostics.passive_fill_share,
                "avg_inventory": ev.fill_diagnostics.avg_inventory,
                "max_inventory": ev.fill_diagnostics.max_inventory,
                "turnover": ev.fill_diagnostics.turnover,
            },
            "by_symbol": {
                sym: {
                    "raw_pnl": ae.raw_pnl,
                    "transfer_score": ae.transfer_score,
                    "verdict": ae.verdict,
                    "passive_fill_share": ae.passive_fill_share,
                    "scenario_gap": ae.scenario_gap,
                }
                for sym, ae in ev.by_symbol.items()
            },
            "scenario_pnls": {
                sc: sum(m.get("total_pnl", 0) for m in metrics) / max(1, len(metrics))
                for sc, metrics in ev.scenario_results.items()
            },
        }

        print(
            f"  pnl={ev.raw_pnl:.0f}, transfer={ev.transfer_score.score:.4f}, verdict={ev.verdict}"
        )

    out = Path("artifacts/baseline_comparison.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
