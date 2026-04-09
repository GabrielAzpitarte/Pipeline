"""Transfer-scored parallel grid sweep on top strategies."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, "src")


def main() -> None:
    """Run transfer-scored sweep with shadow comparison."""
    from agents.tools.strategy_tools import extract_all_params, generate_sweep_grid
    from data.parse_logs import load_round_data
    from experiments.sweep_runner import (
        export_sweep_winners,
        run_sweep_transfer_scored,
    )

    # Load both datasets for cross-validation
    print("Loading datasets...")
    data_d1 = load_round_data(
        Path("data_raw/prices_round_0_day_-1.csv"),
        Path("data_raw/trades_round_0_day_-1.csv"),
    )
    data_d2 = load_round_data(
        Path("data_raw/prices_round_0_day_-2.csv"),
        Path("data_raw/trades_round_0_day_-2.csv"),
    )
    datasets = [data_d1, data_d2]
    print(
        f"Loaded: day_-1 ({len(data_d1.timestamps)} ticks), "
        f"day_-2 ({len(data_d2.timestamps)} ticks)"
    )

    strategies = {
        "microprice_sniper_proven": Path("src/trader/strategies/microprice_sniper_proven.py"),
    }

    for name, path in strategies.items():
        source = path.read_text()
        params = extract_all_params(source)
        print(f"\n{'=' * 70}")
        print(f"Strategy: {name}")
        print(f"Extracted params ({len(params)}): {params}")

        if not params:
            print("  No extractable params — skipping")
            continue

        grid = generate_sweep_grid(params, n_values=3)
        combos = 1
        for vals in grid.values():
            combos *= len(vals)
        total_backtests = combos * len(datasets) * 2  # baseline + conservative
        print(
            f"Full grid: {len(grid)} params x 3 values = {combos} combos"
            f" x {len(datasets)} folds x 2 scenarios = {total_backtests} backtests"
        )
        for p, vals in grid.items():
            print(f"  {p}: {vals}")

        t0 = time.time()
        report = run_sweep_transfer_scored(
            strategy_source=source,
            param_grid=grid,
            datasets=datasets,
            max_workers=12,
        )
        elapsed = time.time() - t0
        print(f"\nCompleted in {elapsed:.1f}s")
        print(f"Rank correlation (old vs new): {report.rank_correlation:.3f}")

        # Show old ranking (raw PnL)
        print("\n--- OLD RANKING (raw backtest PnL) ---")
        print(f"{'Rank':>4}  {'PnL':>8}  Params")
        for i, (p, pnl) in enumerate(report.old_ranking[:10], 1):
            print(f"  {i:>2}  {pnl:>8.0f}  {p}")

        # Show new ranking (transfer score)
        print("\n--- NEW RANKING (transfer score) ---")
        print(
            f"{'Rank':>4}  {'Score':>8}  {'med_blk':>8}  {'min_blk':>8}  "
            f"{'cons_pnl':>8}  {'gap_pen':>8}  {'pass_pen':>8}  Params"
        )
        for i, (p, score, components) in enumerate(report.new_ranking[:10], 1):
            print(
                f"  {i:>2}  {score:>8.4f}  "
                f"{components.get('median_block_pnl', 0):>8.4f}  "
                f"{components.get('min_block_pnl', 0):>8.4f}  "
                f"{components.get('conservative_pnl', 0):>8.4f}  "
                f"{components.get('scenario_gap_penalty', 0):>8.4f}  "
                f"{components.get('passive_dependency_penalty', 0):>8.4f}  "
                f"{p}"
            )

        # Show where rankings disagree
        old_top5 = {str(p) for p, _ in report.old_ranking[:5]}
        new_top5 = {str(p) for p, _, _ in report.new_ranking[:5]}
        only_old = old_top5 - new_top5
        only_new = new_top5 - old_top5
        if only_old or only_new:
            print("\n--- DISAGREEMENTS (top 5) ---")
            if only_old:
                print(f"  In old top 5 but NOT new: {len(only_old)} params")
            if only_new:
                print(f"  In new top 5 but NOT old: {len(only_new)} params")

        # Export new ranking winners
        export_results = [(p, {"total_pnl": score}) for p, score, _ in report.new_ranking[:3]]
        out_dir = Path(f"submissions/sweep_transfer_{name}")
        paths = export_sweep_winners(source, export_results, out_dir, top_n=3)
        print(f"\nExported to: {[str(p) for p in paths]}")


if __name__ == "__main__":
    main()
