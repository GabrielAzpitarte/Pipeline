"""Evaluate strategy candidates deeply and produce comparison report."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, "src")


def main() -> None:
    """Run deep evaluation on top strategy candidates."""
    from agents.tools.strategy_tools import extract_all_params
    from data.parse_logs import load_round_data
    from experiments.evaluator import (
        compare_candidates,
        evaluate_candidates,
        generate_random_variants,
        print_comparison_report,
    )
    from experiments.sweep_runner import _apply_params_to_source

    # Load both datasets
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

    # Define candidates
    microprice_path = Path("src/trader/strategies/microprice_sniper_proven.py")
    microprice_source = microprice_path.read_text()
    microprice_params = extract_all_params(microprice_source)

    strat8_path = Path("test_strategies/strat8_liquidity_momentum.py")
    strat8_source = strat8_path.read_text()

    strat4_path = Path("test_strategies/strat4_taker_penny.py")
    strat4_source = strat4_path.read_text()

    # Build candidate list: proven strategies + a few variants
    candidates: list[tuple[str, str, dict]] = [
        # Proven strategies with default params
        ("microprice_default", microprice_source, {}),
        ("strat4_taker_penny", strat4_source, {}),
        ("strat8_default", strat8_source, {}),
        # CV sweep winner (aggressive params)
        (
            "microprice_cv_winner",
            microprice_source,
            {
                "BASE_SIZE": 10,
                "SKEW_FACTOR": 0.35,
                "EMA_ALPHA": 0.15,
                "MOMENTUM_WEIGHT": 0.21,
                "VOL_WINDOW": 7,
                "EDGE_MULTIPLIER": 1.05,
                "OBI_THRESHOLD": 0.49,
                "UNWIND_THRESHOLD": 35,
            },
        ),
    ]

    # Add a few random variants of the best strategy
    random_variants = generate_random_variants(
        microprice_source, microprice_params, n_variants=3, seed=42
    )
    for vname, vparams in random_variants:
        candidates.append((f"microprice_{vname}", microprice_source, vparams))

    print(f"\nEvaluating {len(candidates)} candidates...")
    for name, _, params in candidates:
        print(f"  - {name}: {params or 'defaults'}")

    # Evaluate
    t0 = time.time()
    evaluations = evaluate_candidates(candidates, datasets)
    elapsed = time.time() - t0
    print(f"\nEvaluation completed in {elapsed:.1f}s")

    # Compare and report
    report = compare_candidates(evaluations)
    print_comparison_report(report)

    # Export recommended strategy as submission file
    best_ev = next((e for e in evaluations if e.name == report.recommended), None)
    if best_ev:
        best_source = None
        for name, source, _params in candidates:
            if name == best_ev.name:
                best_source = source
                break
        if best_source:
            modified = _apply_params_to_source(best_source, best_ev.params)
            out_dir = Path("submissions/evaluated_best")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "strategy.py"
            header = (
                f'"""Recommended by transfer score: {best_ev.name}\n'
                f"Transfer score: {best_ev.transfer_score.score:.4f}\n"
                f"Verdict: {best_ev.verdict}\n"
                f'Params: {best_ev.params}"""\n'
            )
            out_path.write_text(header + modified)
            print(f"Exported recommended strategy to: {out_path}")


if __name__ == "__main__":
    main()
