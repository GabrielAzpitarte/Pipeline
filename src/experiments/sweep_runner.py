"""Run parameter sweeps end-to-end."""

from __future__ import annotations

import copy
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
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
    """Execute strategy source and return the Trader class.

    Runs the code in an isolated namespace. The source must define
    a ``Trader`` class (standard Prosperity submission format).
    """
    namespace: dict[str, Any] = {}
    exec(compile(source_code, "<sweep_strategy>", "exec"), namespace)
    trader_cls = namespace.get("Trader")
    if trader_cls is None:
        raise RuntimeError("Strategy source does not define a Trader class")
    return trader_cls


def _sweep_worker(
    args: tuple[int, dict[str, Any], str, BacktestData, bool],
) -> tuple[int, dict[str, Any], dict[str, float]]:
    """Run one sweep combo. Top-level function for ProcessPoolExecutor (picklable).

    Args:
        args: Tuple of (index, params, source_code, data, fast).

    Returns:
        Tuple of (index, params, metrics_dict).
    """
    index, params, source_code, data, _fast = args

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
        )

        # Process fills
        tick_own_trades: dict[str, list[Trade]] = {}
        for symbol, fill_list in fills.items():
            tick_own_trades[symbol] = []
            for fill in fill_list:
                pnl_tracker.record_fill(symbol, fill.price, fill.quantity)
                positions[symbol] = positions.get(symbol, 0) + fill.quantity
                total_fills += 1
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

    final_pnl = pnl_tracker.total_pnl(mid_prices)
    metrics = {
        "total_pnl": final_pnl,
        "final_cash": pnl_tracker.cash,
        "total_fills": float(total_fills),
    }
    return index, params, metrics


def run_sweep_parallel(
    strategy_source: str,
    param_grid: dict[str, list[Any]],
    data: BacktestData,
    max_workers: int = 12,
    fast: bool = False,
) -> list[tuple[dict[str, Any], dict[str, float]]]:
    """Run a full grid sweep in parallel using multiprocessing.

    Args:
        strategy_source: Raw .py source code of the strategy.
        param_grid: Parameter grid, e.g. ``{"BASE_SIZE": [10, 12, 15], ...}``.
        data: Parsed backtest data (read-only, passed to each worker).
        max_workers: Number of parallel worker processes.
        fast: Unused (kept for API compatibility).

    Returns:
        List of ``(params, metrics)`` tuples sorted by ``total_pnl`` descending.
    """
    combos = grid_sweep(param_grid)
    total = len(combos)
    _log.info("Parallel sweep: %d combinations, %d workers", total, max_workers)

    # Build task arguments
    tasks = [(i, combo, strategy_source, data, fast) for i, combo in enumerate(combos)]

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
