"""Shared utility functions for the trader package."""

from __future__ import annotations

import hashlib
import json
from typing import Any


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
