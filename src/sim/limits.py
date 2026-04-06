"""Position and order limits enforced by the simulator."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trader.datamodel import Order

POSITION_LIMITS: dict[str, int] = {
    # Prosperity 3
    "AMETHYSTS": 20,
    "STARFRUIT": 20,
    "ORCHIDS": 100,
    "ROSES": 60,
    "CHOCOLATE": 250,
    "STRAWBERRIES": 350,
    "GIFT_BASKET": 60,
    # Prosperity 4 tutorial round
    "EMERALDS": 80,
    "TOMATOES": 80,
    # Prosperity 3/4 (other rounds)
    "RAINFOREST_RESIN": 50,
    "KELP": 50,
    "SQUID_INK": 50,
}


def get_limit(product: str) -> int:
    """Return the position limit for a product, default 20."""
    return POSITION_LIMITS.get(product, 20)


def enforce_limits(
    orders: dict[str, list[Order]],
    positions: dict[str, int],
) -> dict[str, list[Order]]:
    """Prosperity-faithful all-or-nothing position limit enforcement.

    For each symbol, if ALL orders were filled simultaneously, would the
    resulting long or short position exceed the limit? If so, ALL orders
    for that symbol are rejected.

    This differs from ``trader.risk.validate_orders`` which filters
    individual orders incrementally.
    """
    accepted: dict[str, list[Order]] = {}

    for symbol, order_list in orders.items():
        limit = get_limit(symbol)
        current_pos = positions.get(symbol, 0)

        total_buy = sum(o.quantity for o in order_list if o.quantity > 0)
        total_sell = sum(o.quantity for o in order_list if o.quantity < 0)

        max_long = current_pos + total_buy
        max_short = current_pos + total_sell

        if abs(max_long) > limit or abs(max_short) > limit:
            continue  # reject ALL orders for this symbol

        accepted[symbol] = order_list

    return accepted
