"""Run parameter sweeps end-to-end."""

from __future__ import annotations

import copy
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data.parse_logs import BacktestData, load_round_data
from experiments.config import ExperimentConfig
from experiments.runner import ExperimentResult, run_experiment
from experiments.sweeps import grid_sweep
from trader.logging_utils import get_logger

_log = get_logger("experiments.sweep_runner")


def run_sweep(
    config: ExperimentConfig,
    fast: bool = False,
    save: bool = True,
    artifacts_dir: Path | None = None,
) -> list[ExperimentResult]:
    """Run a grid sweep from an ExperimentConfig.

    Reads the ``[sweep]`` section from ``config.raw`` to get param grids.
    Falls back to ``[params]`` as a single-point grid if no ``[sweep]``.
    """
    sweep_section: dict[str, Any] = config.raw.get("sweep", {})
    if not sweep_section:
        _log.info("No [sweep] section; running single experiment with [params]")
        sweep_section = {k: [v] for k, v in config.strategy_params.items()}

    if not sweep_section:
        # No params at all — run once with empty params
        sweep_section = {"_dummy": [None]}

    combos = grid_sweep(sweep_section)
    _log.info("Sweep: %d parameter combinations", len(combos))

    data = load_round_data(config.prices_path, config.trades_path)
    results: list[ExperimentResult] = []

    for i, params in enumerate(combos):
        # Remove dummy key if present
        clean_params = {k: v for k, v in params.items() if k != "_dummy"}
        run_name = f"{config.name}_sweep_{i:04d}"
        _log.info("Sweep run %d/%d: %s %s", i + 1, len(combos), run_name, clean_params)

        result = run_experiment(
            name=run_name,
            strategy=config.strategy,
            data=data,
            config=config.sim_config,
            dataset_description=config.dataset_description,
            tags=[*config.tags, "sweep", config.name],
            strategy_params=clean_params,
            save=save,
            artifacts_dir=artifacts_dir,
            fast=fast,
        )
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Parallel grid sweep — runs strategies directly via exec(), no registry
# ---------------------------------------------------------------------------


def _apply_params_to_source(source_code: str, overrides: dict[str, Any]) -> str:
    """Inject parameter overrides into strategy source code.

    Handles two patterns:
      1. Module-level constants: ``BASE_SIZE = 15``
      2. ``p.get()`` defaults: ``p.get("base_size", 15)``
    """
    result = source_code
    for name, val in overrides.items():
        result = re.sub(
            rf"^({re.escape(name)})\s*=\s*\S+\s*$",
            rf"\1 = {val}",
            result,
            flags=re.MULTILINE,
        )
        result = re.sub(
            rf'(p\.get\("{re.escape(name)}",\s*)[^)]+(\))',
            rf"\g<1>{val}\2",
            result,
        )
    return result


def _make_trader_from_source(source_code: str) -> Any:
    """Execute strategy source and return a Trader-compatible class.

    Handles two formats:
    1. Standalone ``class Trader`` with ``run()`` (submission format)
    2. Registry-style ``@register("name")`` class with ``compute_orders()``
       — wraps it in a Trader adapter with ``run()``
    """
    namespace: dict[str, Any] = {}
    exec(compile(source_code, "<sweep_strategy>", "exec"), namespace)

    # Try standard Trader class first
    trader_cls = namespace.get("Trader")
    if trader_cls is not None:
        return trader_cls

    # Look for any class with compute_orders (registry-style)
    for obj in namespace.values():
        if isinstance(obj, type) and hasattr(obj, "compute_orders"):
            return _wrap_strategy_cls(obj)

    raise RuntimeError("Strategy source does not define a Trader class")


def _wrap_strategy_cls(cls: type) -> type:
    """Wrap a compute_orders-style strategy in a Trader-compatible class."""

    class _WrappedTrader:
        def __init__(self) -> None:
            self._strategy = cls()

        def run(self, state: Any) -> tuple[dict, int, str]:
            orders = self._strategy.compute_orders(state)
            return orders, 0, ""

    return _WrappedTrader


def _sweep_worker(
    args: tuple[int, dict[str, Any], str, BacktestData, bool, float],
) -> tuple[int, dict[str, Any], dict[str, float]]:
    """Run one sweep combo. Top-level function for ProcessPoolExecutor (picklable).

    Args:
        args: Tuple of (index, params, source_code, data, fast, passive_fill_rate).

    Returns:
        Tuple of (index, params, metrics_dict).
    """
    index, params, source_code, data, _fast, passive_fill_rate = args

    # Inject params and build Trader
    modified_source = _apply_params_to_source(source_code, params)
    trader_cls = _make_trader_from_source(modified_source)
    trader = trader_cls()

    # Run simulation directly (no registry needed)
    from sim.engine import _build_order_depth
    from sim.limits import enforce_limits
    from sim.matching import MarketTrade, TradeMatchingMode, match_orders
    from sim.pnl import PnLTracker
    from trader.datamodel import Listing, Observation, OrderDepth, Trade, TradingState

    pnl_tracker = PnLTracker()
    positions: dict[str, int] = {}
    own_trades: dict[str, list[Trade]] = {}
    trader_data: str = ""
    mid_prices: dict[str, float] = {}
    total_fills = 0
    passive_fills = 0
    aggressive_fills = 0
    position_sum = 0  # for avg inventory
    # Per-symbol tracking
    per_sym_fills: dict[str, int] = {}
    per_sym_passive: dict[str, int] = {}
    per_sym_aggressive: dict[str, int] = {}
    per_sym_pos_sum: dict[str, float] = {}
    per_sym_max_pos: dict[str, int] = {}

    for timestamp in data.timestamps:
        order_depths: dict[str, OrderDepth] = {}
        mid_prices = {}
        listings: dict[str, Listing] = {}

        for product, price_row in data.prices.get(timestamp, {}).items():
            order_depths[product] = _build_order_depth(
                price_row.bid_prices,
                price_row.bid_volumes,
                price_row.ask_prices,
                price_row.ask_volumes,
            )
            mid_prices[product] = price_row.mid_price
            listings[product] = Listing(product, product, "SEASHELLS")

        raw_trades: dict[str, list[Trade]] = {}
        market_trades_mt: dict[str, list[MarketTrade]] = {}
        for product, trade_rows in data.trades.get(timestamp, {}).items():
            trades_list: list[Trade] = []
            mt_list: list[MarketTrade] = []
            for tr in trade_rows:
                t = Trade(
                    symbol=tr.symbol,
                    price=tr.price,
                    quantity=tr.quantity,
                    buyer=tr.buyer,
                    seller=tr.seller,
                    timestamp=tr.timestamp,
                )
                trades_list.append(t)
                mt_list.append(
                    MarketTrade(trade=t, buy_quantity=tr.quantity, sell_quantity=tr.quantity)
                )
            raw_trades[product] = trades_list
            market_trades_mt[product] = mt_list

        state = TradingState(
            timestamp=timestamp,
            traderData=trader_data,
            listings=listings,
            order_depths=copy.deepcopy(order_depths),
            own_trades=own_trades,
            market_trades={
                s: [
                    Trade(t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp) for t in tl
                ]
                for s, tl in raw_trades.items()
            },
            position=dict(positions),
            observations=Observation(),
        )

        # Call trader
        result = trader.run(state)
        if isinstance(result, tuple):
            raw_orders = result[0]
            trader_data = result[2] if len(result) > 2 else ""
        else:
            raw_orders = result
            trader_data = ""

        # Enforce position limits
        valid_orders = enforce_limits(raw_orders, positions)

        # Match orders
        fills = match_orders(
            valid_orders,
            order_depths,
            market_trades_mt,
            TradeMatchingMode.ALL,
            passive_fill_rate=passive_fill_rate,
        )

        # Process fills
        tick_own_trades: dict[str, list[Trade]] = {}
        for symbol, fill_list in fills.items():
            tick_own_trades[symbol] = []
            for fill in fill_list:
                pnl_tracker.record_fill(symbol, fill.price, fill.quantity)
                positions[symbol] = positions.get(symbol, 0) + fill.quantity
                total_fills += 1
                per_sym_fills[symbol] = per_sym_fills.get(symbol, 0) + 1
                if fill.against == "market_trade":
                    passive_fills += 1
                    per_sym_passive[symbol] = per_sym_passive.get(symbol, 0) + 1
                else:
                    aggressive_fills += 1
                    per_sym_aggressive[symbol] = per_sym_aggressive.get(symbol, 0) + 1
                tick_own_trades[symbol].append(
                    Trade(
                        symbol=symbol,
                        price=fill.price,
                        quantity=abs(fill.quantity),
                        buyer="SUBMISSION" if fill.quantity > 0 else "",
                        seller="SUBMISSION" if fill.quantity < 0 else "",
                        timestamp=timestamp,
                    )
                )
        own_trades = tick_own_trades

        # Track inventory for diagnostics
        position_sum += sum(abs(v) for v in positions.values())
        for sym, pos in positions.items():
            per_sym_pos_sum[sym] = per_sym_pos_sum.get(sym, 0.0) + abs(pos)
            per_sym_max_pos[sym] = max(per_sym_max_pos.get(sym, 0), abs(pos))

    n_ticks = len(data.timestamps)
    final_pnl = pnl_tracker.total_pnl(mid_prices)
    total_volume = sum(abs(v) for v in pnl_tracker.positions.values())
    passive_share = passive_fills / total_fills if total_fills > 0 else 0.0
    # Per-symbol PnL (cash + unrealized)
    products = set(pnl_tracker.cash_by_product.keys()) | set(positions.keys())
    by_symbol: dict[str, dict[str, float]] = {}
    for sym in products:
        sym_cash = pnl_tracker.cash_by_product.get(sym, 0.0)
        sym_pos = positions.get(sym, 0)
        sym_mid = mid_prices.get(sym, 0.0)
        sym_fills = per_sym_fills.get(sym, 0)
        sym_passive = per_sym_passive.get(sym, 0)
        by_symbol[sym] = {
            "pnl": sym_cash + sym_pos * sym_mid,
            "cash": sym_cash,
            "fills": float(sym_fills),
            "passive_fills": float(sym_passive),
            "aggressive_fills": float(per_sym_aggressive.get(sym, 0)),
            "passive_fill_share": sym_passive / max(1, sym_fills),
            "avg_inventory": per_sym_pos_sum.get(sym, 0.0) / max(1, n_ticks),
            "max_inventory": float(per_sym_max_pos.get(sym, 0)),
        }

    metrics = {
        "total_pnl": final_pnl,
        "final_cash": pnl_tracker.cash,
        "total_fills": float(total_fills),
        "passive_fills": float(passive_fills),
        "aggressive_fills": float(aggressive_fills),
        "passive_fill_share": passive_share,
        "avg_inventory": position_sum / n_ticks if n_ticks > 0 else 0.0,
        "max_inventory": float(max((abs(v) for v in positions.values()), default=0)),
        "turnover": float(total_volume) / n_ticks if n_ticks > 0 else 0.0,
        "by_symbol": by_symbol,
    }
    return index, params, metrics


def run_sweep_parallel(
    strategy_source: str,
    param_grid: dict[str, list[Any]],
    data: BacktestData,
    max_workers: int = 12,
    fast: bool = False,
    passive_fill_rate: float = 1.0,
) -> list[tuple[dict[str, Any], dict[str, float]]]:
    """Run a full grid sweep in parallel using multiprocessing.

    Args:
        strategy_source: Raw .py source code of the strategy.
        param_grid: Parameter grid, e.g. ``{"BASE_SIZE": [10, 12, 15], ...}``.
        data: Parsed backtest data (read-only, passed to each worker).
        max_workers: Number of parallel worker processes.
        fast: Unused (kept for API compatibility).
        passive_fill_rate: Passive fill rate for matching (1.0 = baseline).

    Returns:
        List of ``(params, metrics)`` tuples sorted by ``total_pnl`` descending.
    """
    combos = grid_sweep(param_grid)
    total = len(combos)
    _log.info("Parallel sweep: %d combinations, %d workers", total, max_workers)

    # Build task arguments
    tasks = [
        (i, combo, strategy_source, data, fast, passive_fill_rate) for i, combo in enumerate(combos)
    ]

    results: list[tuple[dict[str, Any], dict[str, float]]] = []
    best_pnl = float("-inf")
    completed = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_sweep_worker, task): task[0] for task in tasks}

        for future in as_completed(futures):
            completed += 1
            try:
                _index, params, metrics = future.result()
                results.append((params, metrics))
                pnl = metrics.get("total_pnl", float("-inf"))
                if pnl > best_pnl:
                    best_pnl = pnl
                if completed % 50 == 0 or completed == total:
                    _log.info(
                        "Sweep progress: %d/%d (%.0f%%), best PnL so far: %.2f",
                        completed,
                        total,
                        100 * completed / total,
                        best_pnl,
                    )
            except Exception:
                _log.exception("Sweep worker failed for task %d", futures[future])

    # Sort by total_pnl descending
    results.sort(key=lambda r: r[1].get("total_pnl", float("-inf")), reverse=True)

    if results:
        _log.info(
            "Sweep complete: %d results, best PnL=%.2f, params=%s",
            len(results),
            results[0][1].get("total_pnl", 0),
            results[0][0],
        )

    return results


def run_sweep_cross_validated(
    strategy_source: str,
    param_grid: dict[str, list[Any]],
    datasets: list[BacktestData],
    max_workers: int = 12,
    rank_by: str = "min",
) -> list[tuple[dict[str, Any], list[dict[str, float]]]]:
    """Cross-validated sweep: run full grid on each dataset, rank by aggregate.

    For each param combo, runs on ALL datasets independently. Results are
    ranked by the aggregate PnL metric across datasets.

    Args:
        strategy_source: Raw .py source code of the strategy.
        param_grid: Parameter grid, e.g. ``{"BASE_SIZE": [10, 12, 15], ...}``.
        datasets: List of BacktestData objects (one per fold).
        max_workers: Number of parallel worker processes.
        rank_by: Aggregation method — ``"min"`` (most conservative),
                 ``"mean"``, or ``"geomean"`` (geometric mean).

    Returns:
        List of ``(params, [metrics_per_dataset])`` sorted by aggregate PnL desc.
    """
    import math

    # Run sweep on each dataset
    per_dataset_results: list[list[tuple[dict[str, Any], dict[str, float]]]] = []
    for i, data in enumerate(datasets):
        _log.info("Cross-validation fold %d/%d", i + 1, len(datasets))
        fold_results = run_sweep_parallel(
            strategy_source=strategy_source,
            param_grid=param_grid,
            data=data,
            max_workers=max_workers,
        )
        per_dataset_results.append(fold_results)

    # Index results by params (convert dict to hashable key)
    def _params_key(params: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
        return tuple(sorted(params.items()))

    # Build lookup: params_key -> [metrics_d1, metrics_d2, ...]
    combined: dict[tuple[tuple[str, Any], ...], list[dict[str, float]]] = {}
    all_params: dict[tuple[tuple[str, Any], ...], dict[str, Any]] = {}

    for fold_results in per_dataset_results:
        for params, metrics in fold_results:
            key = _params_key(params)
            all_params[key] = params
            combined.setdefault(key, []).append(metrics)

    # Only keep combos that ran on ALL datasets
    n_folds = len(datasets)
    complete = {k: v for k, v in combined.items() if len(v) == n_folds}

    # Compute aggregate PnL and sort
    def _aggregate_pnl(metrics_list: list[dict[str, float]]) -> float:
        pnls = [m.get("total_pnl", 0.0) for m in metrics_list]
        if not pnls:
            return float("-inf")
        if rank_by == "min":
            return min(pnls)
        if rank_by == "mean":
            return sum(pnls) / len(pnls)
        if rank_by == "geomean":
            # Handle negative PnLs: shift to positive, compute geomean, shift back
            min_pnl = min(pnls)
            if min_pnl <= 0:
                shift = abs(min_pnl) + 1
                shifted = [p + shift for p in pnls]
                gm = math.exp(sum(math.log(s) for s in shifted) / len(shifted))
                return gm - shift
            return math.exp(sum(math.log(p) for p in pnls) / len(pnls))
        return min(pnls)  # fallback

    ranked = sorted(
        [(all_params[k], v) for k, v in complete.items()],
        key=lambda r: _aggregate_pnl(r[1]),
        reverse=True,
    )

    if ranked:
        best_params, best_metrics = ranked[0]
        pnls = [m.get("total_pnl", 0.0) for m in best_metrics]
        _log.info(
            "CV sweep complete: %d combos, rank_by=%s, best aggregate=%.2f, "
            "per-fold PnLs=%s, params=%s",
            len(ranked),
            rank_by,
            _aggregate_pnl(best_metrics),
            [f"{p:.0f}" for p in pnls],
            best_params,
        )

    return ranked


def export_sweep_winners(
    source_code: str,
    results: list[tuple[dict[str, Any], dict[str, float]]],
    output_dir: Path,
    top_n: int = 3,
) -> list[Path]:
    """Write top N sweep results as submission-ready .py files.

    Applies the winning parameters to the strategy source code and writes
    each to ``output_dir/rank_N.py``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for rank, (params, metrics) in enumerate(results[:top_n], 1):
        modified = _apply_params_to_source(source_code, params)
        pnl = metrics.get("total_pnl", 0)
        header = f'"""Sweep rank {rank} — PnL: {pnl:.0f}, params: {params}"""\n'
        filepath = output_dir / f"rank_{rank}.py"
        filepath.write_text(header + modified)
        paths.append(filepath)
        _log.info("Exported rank %d (PnL=%.0f) to %s", rank, pnl, filepath)

    return paths


# ---------------------------------------------------------------------------
# Transfer-scored sweep (Steps 4, 10)
# ---------------------------------------------------------------------------


@dataclass
class SweepComparisonReport:
    """Side-by-side old vs new ranking from a transfer-scored sweep."""

    old_ranking: list[tuple[dict[str, Any], float]]
    new_ranking: list[tuple[dict[str, Any], float, dict[str, float]]]
    rank_correlation: float


def run_sweep_transfer_scored(
    strategy_source: str,
    param_grid: dict[str, list[Any]],
    datasets: list[BacktestData],
    max_workers: int = 12,
    score_weights: dict[str, float] | None = None,
) -> SweepComparisonReport:
    """Full transfer-scored sweep with shadow comparison.

    For each param combo:
    1. Run under baseline mode (passive_fill_rate=1.0) on all datasets
    2. Run under conservative mode (passive_fill_rate=0.3) on all datasets
    3. Compute multi-scale robustness metrics
    4. Compute fill diagnostics
    5. Compute transfer score
    6. Return both old (raw PnL) and new (transfer score) rankings

    Args:
        strategy_source: Raw .py source code.
        param_grid: Parameter grid for sweep.
        datasets: List of BacktestData (typically day_-1 and day_-2).
        max_workers: Number of parallel workers.
        score_weights: Override default transfer score weights.

    Returns:
        SweepComparisonReport with old and new rankings.
    """
    from analytics.robustness import (
        MultiScaleMetrics,
        TransferScore,
        add_cross_day_info,
        compute_fill_diagnostics,
        compute_normalization_maxes,
        compute_transfer_score,
    )

    _log.info("Transfer-scored sweep: %d datasets, baseline + conservative", len(datasets))

    # Phase 1: Run baseline sweep on all datasets
    baseline_per_dataset: list[list[tuple[dict[str, Any], dict[str, float]]]] = []
    for i, data in enumerate(datasets):
        _log.info("Baseline sweep on dataset %d/%d", i + 1, len(datasets))
        fold = run_sweep_parallel(
            strategy_source=strategy_source,
            param_grid=param_grid,
            data=data,
            max_workers=max_workers,
            passive_fill_rate=1.0,
        )
        baseline_per_dataset.append(fold)

    # Phase 2: Run conservative sweep on all datasets
    conservative_per_dataset: list[list[tuple[dict[str, Any], dict[str, float]]]] = []
    for i, data in enumerate(datasets):
        _log.info("Conservative sweep on dataset %d/%d", i + 1, len(datasets))
        fold = run_sweep_parallel(
            strategy_source=strategy_source,
            param_grid=param_grid,
            data=data,
            max_workers=max_workers,
            passive_fill_rate=0.3,
        )
        conservative_per_dataset.append(fold)

    # Phase 3: Join results by params
    def _params_key(params: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
        return tuple(sorted(params.items()))

    # Index all results
    baseline_by_params: dict[tuple[tuple[str, Any], ...], list[dict[str, float]]] = {}
    conservative_by_params: dict[tuple[tuple[str, Any], ...], list[dict[str, float]]] = {}
    all_params_map: dict[tuple[tuple[str, Any], ...], dict[str, Any]] = {}

    for fold in baseline_per_dataset:
        for params, metrics in fold:
            key = _params_key(params)
            all_params_map[key] = params
            baseline_by_params.setdefault(key, []).append(metrics)

    for fold in conservative_per_dataset:
        for params, metrics in fold:
            key = _params_key(params)
            conservative_by_params.setdefault(key, []).append(metrics)

    # Phase 4: Compute transfer scores
    n_datasets = len(datasets)
    all_multi_scale: list[MultiScaleMetrics] = []
    all_scenario_pnls: list[dict[str, float]] = []
    scored: list[tuple[dict[str, Any], float, dict[str, float], TransferScore]] = []

    for key, baseline_metrics_list in baseline_by_params.items():
        if len(baseline_metrics_list) < n_datasets:
            continue
        conservative_list = conservative_by_params.get(key, [])
        if len(conservative_list) < n_datasets:
            continue

        params = all_params_map[key]

        # Use first dataset's PnL series for multi-scale (sweep worker doesn't return series,
        # so approximate from total_pnl split into equal blocks)
        baseline_pnl = sum(m["total_pnl"] for m in baseline_metrics_list) / n_datasets
        conservative_pnl = sum(m["total_pnl"] for m in conservative_list) / n_datasets

        # Multi-scale: approximate blocks from per-dataset PnLs
        cross_day_pnls = [m["total_pnl"] for m in baseline_metrics_list]
        multi_scale = MultiScaleMetrics(
            full_pnl=baseline_pnl,
            block_pnls=cross_day_pnls,  # treat each dataset as a "block"
            median_block_pnl=sorted(cross_day_pnls)[len(cross_day_pnls) // 2],
            min_block_pnl=min(cross_day_pnls),
            lower_quantile_pnl=sorted(cross_day_pnls)[0],
            positive_block_rate=sum(1 for p in cross_day_pnls if p > 0) / len(cross_day_pnls),
            block_pnl_std=_std(cross_day_pnls),
        )
        add_cross_day_info(multi_scale, cross_day_pnls)

        # Average metrics across datasets for diagnostics
        avg_metrics: dict[str, float] = {}
        for k2 in baseline_metrics_list[0]:
            avg_metrics[k2] = sum(m.get(k2, 0.0) for m in baseline_metrics_list) / n_datasets

        scenario_pnls = {"baseline": baseline_pnl, "conservative": conservative_pnl}
        all_multi_scale.append(multi_scale)
        all_scenario_pnls.append(scenario_pnls)

        scored.append((params, baseline_pnl, avg_metrics, TransferScore(score=0.0)))

    # Compute normalization maxes from all candidates
    norm_maxes = compute_normalization_maxes(all_multi_scale, all_scenario_pnls)

    # Rescore with normalization
    final_scored: list[tuple[dict[str, Any], float, dict[str, float], TransferScore]] = []
    for i, (params, baseline_pnl, avg_metrics, _) in enumerate(scored):
        ms = all_multi_scale[i]
        diag = compute_fill_diagnostics(avg_metrics)
        sp = all_scenario_pnls[i]
        ts = compute_transfer_score(ms, diag, sp, score_weights, norm_maxes)
        final_scored.append((params, baseline_pnl, avg_metrics, ts))

    # Build old ranking (by raw baseline PnL)
    old_ranking = sorted(
        [(p, bpnl) for p, bpnl, _, _ in final_scored],
        key=lambda r: r[1],
        reverse=True,
    )

    # Build new ranking (by transfer score)
    new_ranking = sorted(
        [(p, ts.score, ts.components) for p, _, _, ts in final_scored],
        key=lambda r: r[1],
        reverse=True,
    )

    # Compute rank correlation (Spearman)
    old_order = {_params_key(p): i for i, (p, _) in enumerate(old_ranking)}
    new_order = {_params_key(p): i for i, (p, _, _) in enumerate(new_ranking)}
    common_keys = set(old_order.keys()) & set(new_order.keys())
    if len(common_keys) > 1:
        n_common = len(common_keys)
        d_sq_sum = sum((old_order[k] - new_order[k]) ** 2 for k in common_keys)
        rank_corr = 1 - (6 * d_sq_sum) / (n_common * (n_common**2 - 1))
    else:
        rank_corr = 0.0

    _log.info(
        "Transfer-scored sweep complete: %d combos, rank correlation=%.3f",
        len(final_scored),
        rank_corr,
    )
    if new_ranking:
        _log.info(
            "Old #1: PnL=%.0f, params=%s",
            old_ranking[0][1],
            old_ranking[0][0],
        )
        _log.info(
            "New #1: score=%.4f, params=%s",
            new_ranking[0][1],
            new_ranking[0][0],
        )

    return SweepComparisonReport(
        old_ranking=old_ranking,
        new_ranking=new_ranking,
        rank_correlation=rank_corr,
    )


def _std(values: list[float]) -> float:
    """Standard deviation of a list of values."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return variance**0.5
