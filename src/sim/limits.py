"""Position and order limits enforced by the simulator."""

from __future__ import annotations

POSITION_LIMITS: dict[str, int] = {
    "AMETHYSTS": 20,
    "STARFRUIT": 20,
    "ORCHIDS": 100,
    "ROSES": 60,
    "CHOCOLATE": 250,
    "STRAWBERRIES": 350,
    "GIFT_BASKET": 60,
}


def get_limit(product: str) -> int:
    """Return the position limit for a product, default 20."""
    return POSITION_LIMITS.get(product, 20)
