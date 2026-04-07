"""Run parallel grid sweeps on top 3 strategies."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, "src")


def main() -> None:
    """Run sweeps on the top 3 strategies."""
    from agents.tools.strategy_tools import extract_all_params, generate_sweep_grid
    from data.parse_logs import load_round_data
    from experiments.sweep_runner import export_sweep_winners, run_sweep_parallel

    data = load_round_data(
        Path("data_raw/prices_round_0_day_-1.csv"),
        Path("data_raw/trades_round_0_day_-1.csv"),
    )

    strategies = {
        "microprice_sniper_proven": Path("src/trader/strategies/microprice_sniper_proven.py"),
        "strat8_liquidity_momentum": Path("test_strategies/strat8_liquidity_momentum.py"),
        "strat4_taker_penny": Path("test_strategies/strat4_taker_penny.py"),
    }

    for name, path in strategies.items():
        source = path.read_text()
        params = extract_all_params(source)
        print(f"\n{'='*60}")
        print(f"Strategy: {name}")
        print(f"Extracted params: {params}")

        if not params:
            print("  No extractable params — skipping")
            continue

        grid = generate_sweep_grid(params, n_values=3)

        # Cap at 6 most impactful params to keep combos reasonable
        # Priority: size/threshold params first, then multipliers
        if len(grid) > 6:
            priority_order = [
                "BASE_SIZE",
                "base_size",
                "UNWIND_THRESHOLD",
                "unwind_threshold",
                "SKEW_FACTOR",
                "inventory_skew",
                "EMA_ALPHA",
                "ema_alpha",
                "EDGE_MULTIPLIER",
                "edge_multiplier",
                "MOMENTUM_WEIGHT",
                "momentum_weight",
                "OBI_THRESHOLD",
                "imbalance_threshold",
                "VOL_WINDOW",
                "volatility_window",
            ]
            ordered_keys = sorted(
                grid.keys(),
                key=lambda k: priority_order.index(k) if k in priority_order else 99,
            )
            grid = {k: grid[k] for k in ordered_keys[:6]}

        combos = 1
        for vals in grid.values():
            combos *= len(vals)
        print(f"Grid: {len(grid)} params x 3 values = {combos} combos")
        for p, vals in grid.items():
            print(f"  {p}: {vals}")

        t0 = time.time()
        results = run_sweep_parallel(
            strategy_source=source,
            param_grid=grid,
            data=data,
            max_workers=12,
        )
        elapsed = time.time() - t0

        print(f"\nCompleted in {elapsed:.1f}s")
        print("Top 5 results:")
        for i, (p, m) in enumerate(results[:5], 1):
            print(
                f"  #{i}: PnL={m['total_pnl']:.0f}, fills={m.get('total_fills',0):.0f}, params={p}"
            )

        # Show default params result for comparison
        default_results = [
            (p, m) for p, m in results if all(p.get(k) == params.get(k) for k in params)
        ]
        if default_results:
            _, dm = default_results[0]
            print(f"\nDefault params: PnL={dm['total_pnl']:.0f}")

        out_dir = Path(f"submissions/sweep_{name}")
        paths = export_sweep_winners(source, results, out_dir, top_n=3)
        print(f"Exported to: {[str(p) for p in paths]}")


if __name__ == "__main__":
    main()
