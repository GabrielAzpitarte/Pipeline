"""Execution scenario configurations for simulation.

Scenarios represent different assumptions about how the platform fills
orders. The baseline scenario matches current jmerle-compatible behavior.
Conservative scenarios model stricter fill conditions that better
approximate real platform behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class ExecutionScenario:
    """Configuration for one execution scenario."""

    name: str = "baseline"
    passive_fill_rate: float = 1.0  # 1.0 = fill all, 0.3 = fill 30% at same price
    queue_model: str = "none"  # "none" | "simple"
    trade_match_mode: str = "all"  # TradeMatchingMode value
    trade_split: str = "one_sided"  # "one_sided" (default) | "half" (legacy) | "probabilistic"
    latency_ticks: int = 0  # ticks of order placement delay


# Preset scenarios — each tests a different failure mode
BASELINE = ExecutionScenario(name="baseline")

QUEUE_HOSTILE = ExecutionScenario(
    name="queue_hostile",
    passive_fill_rate=0.5,
    queue_model="simple",
    latency_ticks=1,
)

PASSIVE_HOSTILE = ExecutionScenario(
    name="passive_hostile",
    passive_fill_rate=0.2,
    trade_split="one_sided",
)

TAKER_FAVORABLE = ExecutionScenario(
    name="taker_favorable",
    passive_fill_rate=0.3,
    trade_match_mode="worse",
)

# Legacy mode for regression comparison only
LEGACY_REGRESSION = ExecutionScenario(
    name="legacy_regression",
    trade_split="half",
)

ALL_SCENARIOS = [BASELINE, QUEUE_HOSTILE, PASSIVE_HOSTILE, TAKER_FAVORABLE]


class ScenarioRegistry:
    """Single source of truth for all execution scenarios."""

    _scenarios: ClassVar[dict[str, ExecutionScenario]] = {}

    @classmethod
    def register(cls, scenario: ExecutionScenario) -> None:
        """Register a scenario."""
        cls._scenarios[scenario.name] = scenario

    @classmethod
    def get(cls, name: str) -> ExecutionScenario:
        """Get a scenario by name. Raises ValueError if not found."""
        if name not in cls._scenarios:
            raise ValueError(f"Unknown scenario: {name!r}. Available: {list(cls._scenarios)}")
        return cls._scenarios[name]

    @classmethod
    def all(cls) -> list[ExecutionScenario]:
        """Return all registered scenarios."""
        return list(cls._scenarios.values())

    @classmethod
    def names(cls) -> list[str]:
        """Return all registered scenario names."""
        return list(cls._scenarios.keys())


# Register all presets
for _s in ALL_SCENARIOS:
    ScenarioRegistry.register(_s)


def get_scenario(name: str) -> ExecutionScenario:
    """Look up a preset scenario by name."""
    return ScenarioRegistry.get(name)
