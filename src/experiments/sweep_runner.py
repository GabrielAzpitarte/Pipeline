"""Run parameter sweeps end-to-end."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from data.parse_logs import load_round_data
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
