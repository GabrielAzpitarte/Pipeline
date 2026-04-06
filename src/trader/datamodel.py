"""Prosperity 4 datamodel — faithful recreation of the competition API.

This file is intentionally self-contained with zero internal imports so it
can be copy-pasted directly into a Prosperity submission.
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Type aliases (match Prosperity conventions)
# ---------------------------------------------------------------------------

Symbol = str
Product = str
Position = int
UserId = str
ObservationValue = int
Time = int

# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


class Listing:
    """A tradable instrument on the exchange."""

    def __init__(self, symbol: Symbol, product: Product, denomination: Product) -> None:
        self.symbol = symbol
        self.product = product
        self.denomination = denomination

    def __repr__(self) -> str:
        return f"Listing({self.symbol}, {self.product}, {self.denomination})"


# ---------------------------------------------------------------------------
# Observation helpers
# ---------------------------------------------------------------------------


class ConversionObservation:
    """Market data for cross-product conversion opportunities."""

    def __init__(
        self,
        bidPrice: float,
        askPrice: float,
        transportFees: float,
        exportTariff: float,
        importTariff: float,
        sugarPrice: float,
        sunlightIndex: float,
    ) -> None:
        self.bidPrice = bidPrice
        self.askPrice = askPrice
        self.transportFees = transportFees
        self.exportTariff = exportTariff
        self.importTariff = importTariff
        self.sugarPrice = sugarPrice
        self.sunlightIndex = sunlightIndex

    def __repr__(self) -> str:
        return (
            f"ConversionObservation(bid={self.bidPrice}, ask={self.askPrice}, "
            f"transport={self.transportFees}, export={self.exportTariff}, "
            f"import={self.importTariff}, sugar={self.sugarPrice}, "
            f"sunlight={self.sunlightIndex})"
        )


class Observation:
    """Observations available to the trader each tick."""

    def __init__(
        self,
        plainValueObservations: dict[Product, ObservationValue] | None = None,
        conversionObservations: dict[Product, ConversionObservation] | None = None,
    ) -> None:
        self.plainValueObservations = plainValueObservations or {}
        self.conversionObservations = conversionObservations or {}

    def __repr__(self) -> str:
        return (
            f"Observation(plain={self.plainValueObservations}, "
            f"conversions={self.conversionObservations})"
        )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


class Order:
    """A single order to submit to the exchange.

    ``quantity`` > 0 means BUY, ``quantity`` < 0 means SELL.
    ``price`` is always an integer (units of seashells).
    """

    def __init__(self, symbol: Symbol, price: int, quantity: int) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

    def __repr__(self) -> str:
        return f"Order({self.symbol}, {self.price}, {self.quantity})"


# ---------------------------------------------------------------------------
# OrderDepth
# ---------------------------------------------------------------------------


class OrderDepth:
    """Current order book for a single product.

    ``buy_orders``:  {price: quantity}  — quantities are **positive**.
    ``sell_orders``: {price: quantity}  — quantities are **negative** (Prosperity convention).
    """

    def __init__(self) -> None:
        self.buy_orders: dict[int, int] = {}
        self.sell_orders: dict[int, int] = {}

    def __repr__(self) -> str:
        return f"OrderDepth(buys={self.buy_orders}, sells={self.sell_orders})"


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


class Trade:
    """A single executed trade."""

    def __init__(
        self,
        symbol: Symbol,
        price: int,
        quantity: int,
        buyer: UserId = "",
        seller: UserId = "",
        timestamp: int = 0,
    ) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.buyer = buyer
        self.seller = seller
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return (
            f"Trade({self.symbol}, price={self.price}, qty={self.quantity}, "
            f"buyer={self.buyer}, seller={self.seller}, t={self.timestamp})"
        )


# ---------------------------------------------------------------------------
# TradingState
# ---------------------------------------------------------------------------


class TradingState:
    """The full market snapshot passed to ``Trader.run()`` each tick."""

    def __init__(
        self,
        timestamp: Time,
        traderData: str,
        listings: dict[Symbol, Listing],
        order_depths: dict[Symbol, OrderDepth],
        own_trades: dict[Symbol, list[Trade]],
        market_trades: dict[Symbol, list[Trade]],
        position: dict[Product, Position],
        observations: Observation,
    ) -> None:
        self.timestamp = timestamp
        self.traderData = traderData
        self.listings = listings
        self.order_depths = order_depths
        self.own_trades = own_trades
        self.market_trades = market_trades
        self.position = position
        self.observations = observations

    def __repr__(self) -> str:
        return (
            f"TradingState(t={self.timestamp}, "
            f"products={list(self.listings.keys())}, "
            f"positions={self.position})"
        )


# ---------------------------------------------------------------------------
# JSON encoder (matches Prosperity's built-in encoder)
# ---------------------------------------------------------------------------


class ProsperityEncoder(json.JSONEncoder):
    """JSON encoder that handles datamodel objects."""

    def default(self, o: Any) -> Any:
        if isinstance(
            o, Listing | Observation | ConversionObservation | Order | OrderDepth | Trade
        ):
            return o.__dict__
        if isinstance(o, TradingState):
            return {
                "timestamp": o.timestamp,
                "traderData": o.traderData,
                "listings": o.listings,
                "order_depths": o.order_depths,
                "own_trades": o.own_trades,
                "market_trades": o.market_trades,
                "position": o.position,
                "observations": o.observations,
            }
        return super().default(o)
