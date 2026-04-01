"""Pydantic schemas for market data validation."""

from __future__ import annotations

from pydantic import BaseModel


class Order(BaseModel):
    """A single order."""

    symbol: str
    price: float
    quantity: int
    side: str  # "BUY" or "SELL"


class Trade(BaseModel):
    """A single executed trade."""

    symbol: str
    price: float
    quantity: int
    timestamp: int
    buyer: str = ""
    seller: str = ""


class OrderBookLevel(BaseModel):
    """One level of the order book."""

    price: float
    quantity: int
