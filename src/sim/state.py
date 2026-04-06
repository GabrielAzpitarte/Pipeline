"""Simulation state container."""

from __future__ import annotations

from dataclasses import dataclass, field

from trader.datamodel import OrderDepth, Trade


@dataclass
class SimState:
    """Mutable state carried across simulation ticks."""

    timestamp: int = 0
    positions: dict[str, int] = field(default_factory=dict)
    cash: float = 0.0
    order_depths: dict[str, OrderDepth] = field(default_factory=dict)
    own_trades: dict[str, list[Trade]] = field(default_factory=dict)
    trader_data: str = ""
