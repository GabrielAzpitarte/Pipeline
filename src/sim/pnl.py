"""PnL tracking for simulation runs.

PnL = cash (realized flows) + unrealized (position * mid_price).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PnLTracker:
    """Track cash flows, positions, and PnL across products."""

    cash: float = 0.0
    cash_by_product: dict[str, float] = field(default_factory=dict)
    positions: dict[str, int] = field(default_factory=dict)

    def record_fill(self, product: str, price: int, quantity: int) -> None:
        """Update cash and position after a fill.

        quantity > 0 = buy: cash decreases (we pay).
        quantity < 0 = sell: cash increases (we receive).
        """
        cost = price * quantity
        self.cash -= cost
        self.cash_by_product[product] = self.cash_by_product.get(product, 0.0) - cost
        self.positions[product] = self.positions.get(product, 0) + quantity

    def unrealized_pnl(self, product: str, mid_price: float) -> float:
        """Mark-to-market unrealized PnL for one product."""
        return self.positions.get(product, 0) * mid_price

    def total_pnl(self, mid_prices: dict[str, float]) -> float:
        """Total PnL = cash + sum of unrealized across all products."""
        unrealized = sum(self.positions.get(product, 0) * mp for product, mp in mid_prices.items())
        return self.cash + unrealized

    def total_realised(self) -> float:
        """Backward-compatible: return the cash component only."""
        return self.cash
