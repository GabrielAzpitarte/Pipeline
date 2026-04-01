"""PnL tracking for simulation runs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PnLTracker:
    """Track realised and unrealised PnL across products."""

    realised: dict[str, float] = field(default_factory=dict)
    positions: dict[str, int] = field(default_factory=dict)

    def record_fill(self, product: str, price: float, qty: int) -> None:
        """Update position and realised PnL after a fill."""
        prev = self.positions.get(product, 0)
        self.positions[product] = prev + qty
        self.realised.setdefault(product, 0.0)

    def total_realised(self) -> float:
        """Sum of realised PnL across all products."""
        return sum(self.realised.values())
