"""Run a single experiment: strategy + config + data -> results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from analytics.metrics import compute_all_metrics
from data.parse_logs import BacktestData
from data.storage import save_run
from experiments.models import RunData, sim_result_to_run_data
from experiments.registry import register_run
from sim.engine import SimConfig, SimEngine
from trader.logging_utils import get_logger

_log = get_logger("experiments.runner")


@dataclass
class ExperimentResult:
    """Container for one experiment run."""

    name: str
    run_id: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    run_data: RunData | None = None
    output_dir: Path | None = None


def run_experiment(
    name: str,
    strategy: str,
    data: BacktestData,
    config: SimConfig | None = None,
    dataset_description: str = "",
    tags: list[str] | None = None,
    strategy_params: dict[str, Any] | None = None,
    save: bool = True,
    artifacts_dir: Path | None = None,
    fast: bool = False,
) -> ExperimentResult:
    """Execute one experiment: run sim, compute metrics, persist results.

    Args:
        name: Human-readable experiment name.
        strategy: Strategy name (must be registered).
        data: Parsed backtest data.
        config: SimConfig override. Uses default if None.
        dataset_description: Free-text description of the dataset.
        tags: Optional labels for filtering.
        strategy_params: Parameters passed to the strategy constructor.
        save: If True, persist to disk and register.
        artifacts_dir: Override base directory for artifacts.
        fast: If True, use FastSimEngine instead of SimEngine.

    Returns:
        ExperimentResult with run_id, metrics, and full RunData.
    """
    if config is None:
        config = SimConfig(
            strategy_name=strategy,
            strategy_params=strategy_params or {},
        )
    else:
        config = SimConfig(
            trade_match_mode=config.trade_match_mode,
            strategy_name=strategy,
            strategy_params=strategy_params or config.strategy_params,
            risk_limits=config.risk_limits,
            data_split=config.data_split,
        )

    _log.info("Running experiment %r with strategy %r (fast=%s)", name, strategy, fast)

    if fast:
        from sim.fast_engine import FastSimEngine

        engine_instance = FastSimEngine(config)
    else:
        engine_instance = SimEngine(config)  # type: ignore[assignment]

    sim_result = engine_instance.run(data)

    run_data = sim_result_to_run_data(
        sim_result,
        config,
        dataset_description=dataset_description,
        tags=tags,
    )

    metrics = compute_all_metrics(run_data)

    output_dir: Path | None = None
    if save:
        output_dir = save_run(run_data, base_dir=artifacts_dir)
        register_run(run_data, name=name, base_dir=artifacts_dir)
        _log.info("Saved run %s to %s", run_data.metadata.run_id, output_dir)

    return ExperimentResult(
        name=name,
        run_id=run_data.metadata.run_id,
        config=run_data.metadata.config,
        metrics=metrics,
        run_data=run_data,
        output_dir=output_dir,
    )
