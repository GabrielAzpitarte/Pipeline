"""Simulation state container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimState:
    """Mutable state carried across simulation ticks."""

    timestamp: int = 0
    positions: dict[str, int] = field(default_factory=dict)
    cash: float = 0.0
    orderbooks: dict[str, Any] = field(default_factory=dict)
    trade_history: list[dict[str, Any]] = field(default_factory=list)
