"""Shared utility functions for the trader package."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from trader.datamodel import OrderDepth


def mid_price(bid: float, ask: float) -> float:
    """Return the mid-point between bid and ask."""
    return (bid + ask) / 2.0


def vwap(prices: list[float], volumes: list[float]) -> float:
    """Volume-weighted average price."""
    if not prices or not volumes or len(prices) != len(volumes):
        raise ValueError("prices and volumes must be non-empty and equal length")
    total_volume = sum(volumes)
    if total_volume == 0:
        raise ValueError("Total volume must be > 0")
    return sum(p * v for p, v in zip(prices, volumes, strict=True)) / total_volume


def deterministic_hash(obj: Any) -> str:
    """Return a stable SHA-256 hex digest for a JSON-serialisable object."""
    raw = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def best_bid(depth: OrderDepth) -> int | None:
    """Return the highest bid price, or None if no bids."""
    if not depth.buy_orders:
        return None
    return max(depth.buy_orders.keys())


def best_ask(depth: OrderDepth) -> int | None:
    """Return the lowest ask price, or None if no asks."""
    if not depth.sell_orders:
        return None
    return min(depth.sell_orders.keys())


def mid_price_from_depth(depth: OrderDepth) -> float | None:
    """Return mid-price from an OrderDepth, or None if either side is empty."""
    bid = best_bid(depth)
    ask = best_ask(depth)
    if bid is None or ask is None:
        return None
    return (bid + ask) / 2.0
