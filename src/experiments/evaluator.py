"""Candidate evaluation pipeline — deep evaluation of a few serious candidates.

Replaces sweep-first optimization with evaluate-deep comparison.
Each candidate runs under multiple scenarios on multiple datasets,
producing robustness metrics, fill diagnostics, and a transfer score.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from analytics.robustness import (
    FillDiagnostics,
    MultiScaleMetrics,
    TransferScore,
    add_cross_day_info,
    compute_fill_diagnostics,
    compute_multi_scale,
    compute_transfer_score,
)
from data.parse_logs import BacktestData
from experiments.sweep_runner import (
    _apply_params_to_source,
    _sweep_worker,
)
from sim.scenarios import ALL_SCENARIOS, ExecutionScenario
from trader.logging_utils import get_logger

_log = get_logger("experiments.evaluator")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class AssetEvaluation:
    """Evaluation of one strategy on one product."""

    symbol: str
    raw_pnl: float = 0.0
    scenario_pnls: dict[str, float] = field(default_factory=dict)
    passive_fill_share: float = 0.0
    scenario_gap: float = 0.0
    avg_inventory: float = 0.0
    fills: int = 0
    transfer_score: float = 0.0
    verdict: str = "unknown"


@dataclass
class CandidateEvaluation:
    """Complete deep evaluation of one strategy candidate."""

    name: str
    params: dict[str, Any]

    # Per-scenario, per-dataset metrics
    scenario_results: dict[str, list[dict[str, float]]] = field(default_factory=dict)

    # Robustness
    multi_scale: MultiScaleMetrics = field(default_factory=lambda: MultiScaleMetrics(full_pnl=0.0))
    fill_diagnostics: FillDiagnostics = field(default_factory=FillDiagnostics)

    # Scores
    raw_pnl: float = 0.0
    transfer_score: TransferScore = field(default_factory=lambda: TransferScore(score=0.0))
    calibrated_score: float | None = None

    # Per-asset evaluation
    by_symbol: dict[str, AssetEvaluation] = field(default_factory=dict)

    # Verdict
    verdict: str = "unknown"
    fragility_notes: list[str] = field(default_factory=list)


@dataclass
class ComparisonReport:
    """Side-by-side comparison of evaluated candidates."""

    evaluations: list[CandidateEvaluation]
    rank_by_transfer_score: list[str] = field(default_factory=list)
    rank_by_symbol: dict[str, list[str]] = field(default_factory=dict)
    best_per_asset: dict[str, str] = field(default_factory=dict)
    recommended: str = ""
    safest: str = ""


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------


def evaluate_candidate(
    name: str,
    strategy_source: str,
    params: dict[str, Any],
    datasets: list[BacktestData],
    scenarios: list[ExecutionScenario] | None = None,
    block_size: int = 2000,
) -> CandidateEvaluation:
    """Deeply evaluate one candidate strategy.

    Runs under all scenarios on all datasets, computes block metrics,
    fill diagnostics, transfer score, and assigns a verdict.

    Args:
        name: Human-readable candidate name.
        strategy_source: Raw .py source code.
        params: Parameter overrides to apply.
        datasets: List of BacktestData (typically day_-1 and day_-2).
        scenarios: Execution scenarios to test. Defaults to all 4.
        block_size: Tick count per evaluation block (default 2000 = platform length).
    """
    if scenarios is None:
        scenarios = list(ALL_SCENARIOS)

    modified_source = _apply_params_to_source(strategy_source, params)

    # Run under each scenario x each dataset
    scenario_results: dict[str, list[dict[str, float]]] = {}
    for scenario in scenarios:
        scenario_metrics: list[dict[str, float]] = []
        for data in datasets:
            task = (0, params, modified_source, data, False, scenario.passive_fill_rate)
            _, _, metrics = _sweep_worker(task)
            scenario_metrics.append(metrics)
        scenario_results[scenario.name] = scenario_metrics

    # Compute multi-scale from baseline results
    baseline_metrics_list = scenario_results.get("baseline", [])
    cross_day_pnls = [m.get("total_pnl", 0.0) for m in baseline_metrics_list]
    avg_baseline_pnl = sum(cross_day_pnls) / len(cross_day_pnls) if cross_day_pnls else 0.0

    # Block-level metrics (approximate from per-dataset PnLs)
    multi_scale = compute_multi_scale(cross_day_pnls, block_size=1)
    add_cross_day_info(multi_scale, cross_day_pnls)
    multi_scale.full_pnl = avg_baseline_pnl

    # Fill diagnostics from baseline (average across datasets, skip non-numeric)
    avg_metrics: dict[str, float] = {}
    if baseline_metrics_list:
        for key in baseline_metrics_list[0]:
            val = baseline_metrics_list[0][key]
            if not isinstance(val, int | float):
                continue  # skip nested dicts like by_symbol
            avg_metrics[key] = sum(m.get(key, 0.0) for m in baseline_metrics_list) / len(
                baseline_metrics_list
            )
    diagnostics = compute_fill_diagnostics(avg_metrics)

    # Scenario PnLs for transfer score
    scenario_pnls: dict[str, float] = {}
    for sc_name, sc_metrics in scenario_results.items():
        scenario_pnls[sc_name] = sum(m.get("total_pnl", 0.0) for m in sc_metrics) / max(
            1, len(sc_metrics)
        )

    # Transfer score
    ts = compute_transfer_score(multi_scale, diagnostics, scenario_pnls)

    # Verdict
    verdict, notes = _assign_verdict(scenario_pnls, diagnostics, multi_scale)

    # Per-asset evaluation
    by_symbol = _compute_per_asset_evaluations(scenario_results, datasets)

    # Recompute total score as portfolio of asset scores if we have per-asset data
    if by_symbol:
        from analytics.robustness import compute_portfolio_score

        asset_scores = {sym: ae.transfer_score for sym, ae in by_symbol.items()}
        portfolio_score = compute_portfolio_score(asset_scores)
        ts = TransferScore(
            score=portfolio_score, components={**ts.components, "portfolio": portfolio_score}
        )

    return CandidateEvaluation(
        name=name,
        params=params,
        scenario_results=scenario_results,
        multi_scale=multi_scale,
        fill_diagnostics=diagnostics,
        raw_pnl=avg_baseline_pnl,
        transfer_score=ts,
        by_symbol=by_symbol,
        verdict=verdict,
        fragility_notes=notes,
    )


def _compute_per_asset_evaluations(
    scenario_results: dict[str, list[dict[str, float]]],
    datasets: list[BacktestData],
) -> dict[str, AssetEvaluation]:
    """Compute per-asset evaluations from scenario results.

    Extracts the ``by_symbol`` dict from each scenario's metrics to build
    per-asset PnL, passive fill share, scenario gap, and a per-asset
    transfer score.
    """
    baseline_list = scenario_results.get("baseline", [])
    if not baseline_list:
        return {}

    # Discover symbols from by_symbol in metrics
    all_symbols: set[str] = set()
    for m in baseline_list:
        bs = m.get("by_symbol")
        if isinstance(bs, dict):
            all_symbols.update(bs.keys())

    if not all_symbols:
        return {}

    result: dict[str, AssetEvaluation] = {}
    n_datasets = len(datasets)

    for sym in sorted(all_symbols):
        # Per-scenario PnL for this symbol
        sym_scenario_pnls: dict[str, float] = {}
        for sc_name, sc_metrics in scenario_results.items():
            pnls: list[float] = []
            for m in sc_metrics:
                bs = m.get("by_symbol", {})
                if isinstance(bs, dict) and sym in bs:
                    pnls.append(bs[sym].get("pnl", 0.0))
            if pnls:
                sym_scenario_pnls[sc_name] = sum(pnls) / len(pnls)

        baseline_pnl = sym_scenario_pnls.get("baseline", 0.0)
        conservative_pnl = sym_scenario_pnls.get("conservative", baseline_pnl)

        # Scenario gap
        gap = (baseline_pnl - conservative_pnl) / baseline_pnl if baseline_pnl > 0 else 0.0

        # Average fill diagnostics for this symbol
        total_fills = 0
        total_passive = 0
        total_inv = 0.0
        for m in baseline_list:
            bs = m.get("by_symbol", {})
            if isinstance(bs, dict) and sym in bs:
                total_fills += int(bs[sym].get("fills", 0))
                total_passive += int(bs[sym].get("passive_fills", 0))
                total_inv += bs[sym].get("avg_inventory", 0.0)
        avg_passive_share = total_passive / max(1, total_fills)
        avg_inv = total_inv / max(1, n_datasets)

        # Per-asset transfer score (simplified — reward PnL, penalize gap + passive)
        asset_score = baseline_pnl / 10000.0  # normalize
        asset_score -= gap * 0.3  # penalize scenario gap
        asset_score -= avg_passive_share * avg_passive_share * 0.2  # penalize passive dependency

        # Per-asset verdict
        sym_verdict = "strong"
        if baseline_pnl <= 0:
            sym_verdict = "reject"
        elif gap > 0.4 or avg_passive_share > 0.9:
            sym_verdict = "fragile"
        elif gap > 0.2 or avg_passive_share > 0.7:
            sym_verdict = "moderate"

        result[sym] = AssetEvaluation(
            symbol=sym,
            raw_pnl=baseline_pnl,
            scenario_pnls=sym_scenario_pnls,
            passive_fill_share=avg_passive_share,
            scenario_gap=gap,
            avg_inventory=avg_inv,
            fills=total_fills,
            transfer_score=asset_score,
            verdict=sym_verdict,
        )

    return result


def _assign_verdict(
    scenario_pnls: dict[str, float],
    diagnostics: FillDiagnostics,
    multi_scale: MultiScaleMetrics,
) -> tuple[str, list[str]]:
    """Assign a verdict and fragility notes based on evaluation metrics."""
    notes: list[str] = []

    baseline = scenario_pnls.get("baseline", 0.0)
    conservative = scenario_pnls.get("conservative", baseline)

    # Scenario gap
    if baseline > 0:
        gap = (baseline - conservative) / baseline
        if gap > 0.40:
            notes.append(f"high scenario gap ({gap:.0%})")
        elif gap > 0.25:
            notes.append(f"moderate scenario gap ({gap:.0%})")

    # Passive dependency
    if diagnostics.passive_fill_share > 0.70:
        notes.append(f"high passive fill dependency ({diagnostics.passive_fill_share:.0%})")
    elif diagnostics.passive_fill_share > 0.50:
        notes.append(f"moderate passive dependency ({diagnostics.passive_fill_share:.0%})")

    # Cross-day consistency
    if multi_scale.cross_day_consistency < 0.80:
        notes.append(f"low cross-day consistency ({multi_scale.cross_day_consistency:.2f})")

    # Inventory
    if diagnostics.max_inventory >= 70:
        notes.append(f"high max inventory ({diagnostics.max_inventory})")

    # Assign verdict
    if baseline <= 0:
        return "reject", ["negative PnL", *notes]
    if any("high" in n for n in notes):
        return "fragile", notes
    if any("moderate" in n for n in notes):
        return "moderate", notes
    return "strong", notes


def evaluate_candidates(
    candidates: list[tuple[str, str, dict[str, Any]]],
    datasets: list[BacktestData],
    scenarios: list[ExecutionScenario] | None = None,
    max_workers: int = 14,
) -> list[CandidateEvaluation]:
    """Evaluate multiple candidates. Uses parallel workers for speed.

    Args:
        candidates: List of (name, source_code, params) tuples.
        datasets: BacktestData objects for cross-day evaluation.
        scenarios: Scenarios to test (defaults to all 4).
        max_workers: Number of parallel workers.

    Returns:
        List of CandidateEvaluation, one per candidate.
    """
    _log.info("Evaluating %d candidates", len(candidates))
    evaluations: list[CandidateEvaluation] = []

    # For now, evaluate sequentially since each candidate is fast (~1s)
    # and internal _sweep_worker already benefits from being lightweight
    for name, source, params in candidates:
        _log.info("Evaluating candidate: %s", name)
        ev = evaluate_candidate(name, source, params, datasets, scenarios)
        evaluations.append(ev)
        _log.info(
            "  %s: raw_pnl=%.0f, transfer=%.4f, verdict=%s",
            name,
            ev.raw_pnl,
            ev.transfer_score.score,
            ev.verdict,
        )

    return evaluations


# ---------------------------------------------------------------------------
# Comparison report
# ---------------------------------------------------------------------------


def compare_candidates(evaluations: list[CandidateEvaluation]) -> ComparisonReport:
    """Produce a comparison report with portfolio and per-asset rankings."""
    by_transfer = sorted(evaluations, key=lambda e: e.transfer_score.score, reverse=True)

    recommended = by_transfer[0].name if by_transfer else ""

    # Safest = strong verdict with best transfer score
    strong = [e for e in by_transfer if e.verdict == "strong"]
    safest = strong[0].name if strong else (by_transfer[0].name if by_transfer else "")

    # Per-asset rankings
    all_symbols: set[str] = set()
    for ev in evaluations:
        all_symbols.update(ev.by_symbol.keys())

    rank_by_symbol: dict[str, list[str]] = {}
    best_per_asset: dict[str, str] = {}
    for sym in sorted(all_symbols):
        ranked = sorted(
            [e for e in evaluations if sym in e.by_symbol],
            key=lambda e: e.by_symbol[sym].transfer_score,
            reverse=True,
        )
        rank_by_symbol[sym] = [e.name for e in ranked]
        if ranked:
            best_per_asset[sym] = ranked[0].name

    return ComparisonReport(
        evaluations=evaluations,
        rank_by_transfer_score=[e.name for e in by_transfer],
        rank_by_symbol=rank_by_symbol,
        best_per_asset=best_per_asset,
        recommended=recommended,
        safest=safest,
    )


def print_comparison_report(report: ComparisonReport) -> None:
    """Pretty-print portfolio and per-asset comparison tables."""
    # Collect all symbols
    all_symbols = sorted(report.rank_by_symbol.keys())
    sym_headers = "".join(f" {s:>10}" for s in all_symbols)

    header = f"{'Candidate':<30} {'Total':>8}{sym_headers} {'Verdict':<10}"
    print("\n" + "=" * len(header))
    print("PORTFOLIO RANKING")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for ev in sorted(report.evaluations, key=lambda e: e.transfer_score.score, reverse=True):
        sym_scores = ""
        for sym in all_symbols:
            ae = ev.by_symbol.get(sym)
            sym_scores += f" {ae.transfer_score:>10.4f}" if ae else f" {'N/A':>10}"
        print(f"{ev.name:<30} {ev.transfer_score.score:>8.4f}{sym_scores} {ev.verdict:<10}")
        if ev.fragility_notes:
            for note in ev.fragility_notes:
                print(f"  {'':30}  -> {note}")

    print("-" * len(header))

    # Per-asset leaderboards
    for sym in all_symbols:
        print(f"\n{'=' * 60}")
        print(f"{sym} LEADERBOARD")
        print(f"{'=' * 60}")
        print(f"{'Candidate':<30} {'Score':>8} {'PnL':>8} {'Gap%':>6} {'Pass%':>6} {'Verdict':<10}")
        print("-" * 60)

        ranked_names = report.rank_by_symbol.get(sym, [])
        for name in ranked_names:
            ev = next((e for e in report.evaluations if e.name == name), None)
            if ev is None:
                continue
            ae = ev.by_symbol.get(sym)
            if ae is None:
                continue
            print(
                f"{name:<30} {ae.transfer_score:>8.4f} {ae.raw_pnl:>8.0f} "
                f"{ae.scenario_gap:>5.0%} {ae.passive_fill_share:>5.0%} {ae.verdict:<10}"
            )

    # Recommendations
    print(f"\n{'=' * 60}")
    print("RECOMMENDATIONS")
    print(f"{'=' * 60}")
    print(f"Best portfolio:   {report.recommended}")
    print(f"Safest:           {report.safest}")
    for sym, name in sorted(report.best_per_asset.items()):
        print(f"Best {sym:<10}:  {name}")
    if len(report.best_per_asset) >= 2:
        names = list(report.best_per_asset.values())
        if len(set(names)) > 1:
            print(
                "\nHYBRID CANDIDATE: "
                + " + ".join(
                    f"{sym} from {name}" for sym, name in sorted(report.best_per_asset.items())
                )
            )
        else:
            print("\nNo hybrid needed — same strategy best for all assets")
    print()


# ---------------------------------------------------------------------------
# Random variant generation
# ---------------------------------------------------------------------------


def generate_random_variants(
    strategy_source: str,
    base_params: dict[str, Any],
    n_variants: int = 5,
    perturbation: float = 0.15,
    seed: int = 42,
) -> list[tuple[str, dict[str, Any]]]:
    """Generate random parameter variants around the base.

    Each numeric param is perturbed by ±perturbation fraction.
    Integer params stay as integers.

    Returns:
        List of (variant_name, params) tuples.
    """
    rng = random.Random(seed)
    variants: list[tuple[str, dict[str, Any]]] = []

    for i in range(n_variants):
        new_params: dict[str, Any] = {}
        for key, val in base_params.items():
            if isinstance(val, int):
                delta = max(1, int(val * perturbation))
                new_params[key] = max(1, val + rng.randint(-delta, delta))
            elif isinstance(val, float):
                delta = val * perturbation
                new_val = val + rng.uniform(-delta, delta)
                new_params[key] = round(max(0.01, new_val), 4)
            else:
                new_params[key] = val
        variants.append((f"variant_{i + 1}", new_params))

    return variants


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def _cache_key(source: str, params: dict[str, Any], scenario: str, data_hash: str) -> str:
    """Generate a cache key for an evaluation result."""
    content = json.dumps(
        {
            "source_hash": hashlib.md5(source.encode()).hexdigest(),
            "params": params,
            "scenario": scenario,
            "data": data_hash,
        },
        sort_keys=True,
    )
    return hashlib.md5(content.encode()).hexdigest()


def _load_cached(cache_dir: Path, key: str) -> dict[str, float] | None:
    """Load cached metrics if available."""
    path = cache_dir / f"{key}.json"
    if path.exists():
        with open(path) as f:
            result: dict[str, float] = json.load(f)
            return result
    return None


def _save_cache(cache_dir: Path, key: str, metrics: dict[str, float]) -> None:
    """Save metrics to cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.json"
    with open(path, "w") as f:
        json.dump(metrics, f)
