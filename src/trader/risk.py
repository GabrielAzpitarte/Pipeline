"""Risk filters applied to every order before execution."""

from __future__ import annotations

from dataclasses import dataclass

from sim.limits import get_limit
from trader.datamodel import Order
from trader.logging_utils import get_logger

_log = get_logger("risk")


@dataclass
class RiskLimits:
    """Hard limits that must never be breached."""

    max_order_size: int = 10
    max_open_orders: int = 50


def check_order(
    order: Order,
    current_position: int,
    product_limit: int | None = None,
    limits: RiskLimits | None = None,
) -> bool:
    """Return True if a single order passes all risk checks."""
    limits = limits or RiskLimits()
    if abs(order.quantity) > limits.max_order_size:
        return False
    pos_limit = product_limit if product_limit is not None else get_limit(order.symbol)
    return abs(current_position + order.quantity) <= pos_limit


def validate_orders(
    orders: dict[str, list[Order]],
    positions: dict[str, int],
    limits: RiskLimits | None = None,
) -> dict[str, list[Order]]:
    """Filter a full order dict, removing orders that violate risk limits.

    Tracks cumulative position impact across multiple orders for the same
    product within a single tick.
    """
    limits = limits or RiskLimits()
    filtered: dict[str, list[Order]] = {}

    for symbol, order_list in orders.items():
        pos = positions.get(symbol, 0)
        accepted: list[Order] = []

        for order in order_list:
            product_limit = get_limit(symbol)
            if check_order(order, pos, product_limit=product_limit, limits=limits):
                accepted.append(order)
                pos += order.quantity
            else:
                _log.warning(
                    "Order rejected: %s (pos=%d, limit=%d)",
                    order,
                    pos,
                    product_limit,
                )

        if accepted:
            filtered[symbol] = accepted

    return filtered
