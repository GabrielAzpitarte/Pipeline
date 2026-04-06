"""CLI for experiment management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from experiments.runner import ExperimentResult

app = typer.Typer(name="experiments", help="Experiment runner CLI.")
console = Console()


@app.command()
def run(
    config: Path = typer.Option(..., "--config", "-c", help="TOML config file"),
    no_save: bool = typer.Option(False, "--no-save", help="Don't persist results"),
    artifacts_dir: Path | None = typer.Option(None, "--artifacts-dir"),
    fast: bool = typer.Option(False, "--fast", help="Use fast simulator"),
) -> None:
    """Run a single experiment from a TOML config file."""
    from data.parse_logs import load_round_data
    from experiments.config import load_config

    cfg = load_config(config)
    data = load_round_data(cfg.prices_path, cfg.trades_path)

    from experiments.runner import run_experiment

    result = run_experiment(
        name=cfg.name,
        strategy=cfg.strategy,
        data=data,
        config=cfg.sim_config,
        dataset_description=cfg.dataset_description,
        tags=cfg.tags,
        strategy_params=cfg.strategy_params,
        save=not no_save,
        artifacts_dir=artifacts_dir,
        fast=fast,
    )

    _print_result(result)


@app.command()
def sweep(
    config: Path = typer.Option(..., "--config", "-c", help="TOML config with sweep section"),
    fast: bool = typer.Option(False, "--fast", help="Use fast simulator"),
    metric: str = typer.Option("total_pnl", "--metric", "-m"),
    top_n: int = typer.Option(10, "--top", "-n"),
    artifacts_dir: Path | None = typer.Option(None, "--artifacts-dir"),
) -> None:
    """Run a parameter sweep from a TOML config file."""
    from experiments.config import load_config
    from experiments.sweep_runner import run_sweep

    cfg = load_config(config)
    results = run_sweep(cfg, fast=fast, artifacts_dir=artifacts_dir)

    ranked = sorted(results, key=lambda r: r.metrics.get(metric, 0.0), reverse=True)
    _print_sweep_results(ranked[:top_n], metric)


@app.command()
def rank(
    tag: str | None = typer.Option(None, "--tag", "-t"),
    strategy: str | None = typer.Option(None, "--strategy", "-s"),
    metric: str = typer.Option("total_pnl", "--metric", "-m"),
    top_n: int = typer.Option(20, "--top", "-n"),
    artifacts_dir: Path | None = typer.Option(None, "--artifacts-dir"),
) -> None:
    """Rank past runs by a metric."""
    from analytics.metrics import compute_all_metrics
    from data.storage import load_run
    from experiments.registry import RegistryEntry, find_runs

    entries = find_runs(strategy=strategy, tag=tag, base_dir=artifacts_dir)
    if not entries:
        console.print("[yellow]No matching runs found.[/yellow]")
        return

    rows: list[tuple[RegistryEntry, dict[str, float]]] = []
    for entry in entries:
        try:
            run_data = load_run(entry.run_id, base_dir=artifacts_dir)
            metrics = compute_all_metrics(run_data)
            rows.append((entry, metrics))
        except FileNotFoundError:
            pass

    rows.sort(key=lambda r: r[1].get(metric, 0.0), reverse=True)
    _print_ranked(rows[:top_n], metric)


@app.command(name="list")
def list_runs(
    tag: str | None = typer.Option(None, "--tag", "-t"),
    strategy: str | None = typer.Option(None, "--strategy", "-s"),
    artifacts_dir: Path | None = typer.Option(None, "--artifacts-dir"),
) -> None:
    """List registered runs."""
    from experiments.registry import find_runs

    entries = find_runs(strategy=strategy, tag=tag, base_dir=artifacts_dir)
    table = Table(title="Registered Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Name")
    table.add_column("Strategy")
    table.add_column("PnL", justify="right")
    table.add_column("Tags")
    for e in entries:
        table.add_row(e.run_id, e.name, e.strategy, f"{e.final_pnl:.2f}", ", ".join(e.tags))
    console.print(table)


def _print_result(result: ExperimentResult) -> None:
    """Pretty-print a single experiment result."""
    table = Table(title=f"Experiment: {result.name}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    for k, v in sorted(result.metrics.items()):
        table.add_row(k, f"{v:.4f}")
    console.print(table)
    console.print(f"Run ID: {result.run_id}")


def _print_sweep_results(results: list[ExperimentResult], metric: str) -> None:
    """Pretty-print ranked sweep results."""
    table = Table(title=f"Sweep Results (ranked by {metric})")
    table.add_column("Rank", justify="right")
    table.add_column("Name")
    table.add_column(metric, justify="right")
    table.add_column("Config")
    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            r.name,
            f"{r.metrics.get(metric, 0.0):.4f}",
            json.dumps(r.config),
        )
    console.print(table)


def _print_ranked(
    rows: list[tuple[Any, dict[str, float]]],
    metric: str,
) -> None:
    """Pretty-print ranked historical runs."""
    table = Table(title=f"Runs ranked by {metric}")
    table.add_column("Rank", justify="right")
    table.add_column("Run ID", style="cyan")
    table.add_column("Strategy")
    table.add_column(metric, justify="right")
    for i, (entry, metrics) in enumerate(rows, 1):
        val = metrics.get(metric, 0.0)
        table.add_row(str(i), entry.run_id, entry.strategy, f"{val:.4f}")
    console.print(table)
