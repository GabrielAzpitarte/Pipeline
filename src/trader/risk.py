"""Risk filters applied to every order before execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskLimits:
    """Hard limits that must never be breached."""

    max_position: int = 20
    max_order_size: int = 10
    max_open_orders: int = 50


def check_order(
    order: dict[str, Any],
    current_position: int,
    limits: RiskLimits | None = None,
) -> bool:
    """Return True if the order passes all risk checks."""
    limits = limits or RiskLimits()
    qty = int(order.get("quantity", 0))
    if abs(qty) > limits.max_order_size:
        return False
    return abs(current_position + qty) <= limits.max_position
