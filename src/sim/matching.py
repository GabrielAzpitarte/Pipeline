"""Order matching logic for the local simulator."""

from __future__ import annotations

from typing import Any


def match_order(
    order: dict[str, Any],
    orderbook: dict[str, Any],
) -> dict[str, Any] | None:
    """Attempt to fill an order against the current orderbook."""
    return None
