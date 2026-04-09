"""Execution scenario configurations for simulation.

Scenarios represent different assumptions about how the platform fills
orders. The baseline scenario matches current jmerle-compatible behavior.
Conservative scenarios model stricter fill conditions that better
approximate real platform behavior.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionScenario:
    """Configuration for one execution scenario."""

    name: str = "baseline"
    passive_fill_rate: float = 1.0  # 1.0 = fill all, 0.3 = fill 30% at same price
    queue_model: str = "none"  # "none" | "simple"
    trade_match_mode: str = "all"  # TradeMatchingMode value
    latency_ticks: int = 0  # ticks of delay (not yet implemented)
    random_seed: int | None = None


# Preset scenarios
BASELINE = ExecutionScenario(name="baseline")

CONSERVATIVE = ExecutionScenario(
    name="conservative",
    passive_fill_rate=0.3,
    queue_model="simple",
)

MEDIUM = ExecutionScenario(
    name="medium",
    passive_fill_rate=0.6,
)

OPTIMISTIC = ExecutionScenario(
    name="optimistic",
    passive_fill_rate=0.9,
)

ALL_SCENARIOS = [BASELINE, CONSERVATIVE, MEDIUM, OPTIMISTIC]


def get_scenario(name: str) -> ExecutionScenario:
    """Look up a preset scenario by name."""
    for s in ALL_SCENARIOS:
        if s.name == name:
            return s
    raise ValueError(f"Unknown scenario: {name!r}. Available: {[s.name for s in ALL_SCENARIOS]}")
