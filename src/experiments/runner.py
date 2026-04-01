"""Run a single experiment: strategy + config + data -> results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExperimentResult:
    """Container for one experiment run."""

    name: str
    config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)


def run_experiment(
    name: str,
    strategy: str,
    data: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> ExperimentResult:
    """Execute one experiment and return results."""
    # TODO: wire up SimEngine + strategy
    return ExperimentResult(name=name, config=config or {})
