"""Pydantic schemas for market data validation and JSON deserialization."""

from __future__ import annotations

from pydantic import BaseModel

from trader import datamodel

# ---------------------------------------------------------------------------
# Low-level schemas (for raw data validation)
# ---------------------------------------------------------------------------


class OrderSchema(BaseModel):
    """A single order."""

    symbol: str
    price: float
    quantity: int
    side: str  # "BUY" or "SELL"


class TradeSchema(BaseModel):
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


# ---------------------------------------------------------------------------
# TradingState deserialization (JSON -> datamodel)
# ---------------------------------------------------------------------------


class ListingSchema(BaseModel):
    """Pydantic model for a Listing."""

    symbol: str
    product: str
    denomination: str = "SEASHELLS"

    def to_datamodel(self) -> datamodel.Listing:
        """Convert to a datamodel Listing."""
        return datamodel.Listing(self.symbol, self.product, self.denomination)


class OrderDepthSchema(BaseModel):
    """Pydantic model for an OrderDepth.

    Keys in buy_orders / sell_orders are price strings (JSON keys are strings).
    """

    buy_orders: dict[str, int] = {}
    sell_orders: dict[str, int] = {}

    def to_datamodel(self) -> datamodel.OrderDepth:
        """Convert to a datamodel OrderDepth."""
        od = datamodel.OrderDepth()
        od.buy_orders = {int(k): v for k, v in self.buy_orders.items()}
        od.sell_orders = {int(k): v for k, v in self.sell_orders.items()}
        return od


class TradeStateSchema(BaseModel):
    """Pydantic model for a Trade inside TradingState."""

    symbol: str
    price: int
    quantity: int
    buyer: str = ""
    seller: str = ""
    timestamp: int = 0

    def to_datamodel(self) -> datamodel.Trade:
        """Convert to a datamodel Trade."""
        return datamodel.Trade(
            self.symbol, self.price, self.quantity, self.buyer, self.seller, self.timestamp
        )


class TradingStateSchema(BaseModel):
    """Pydantic model for loading a TradingState snapshot from JSON."""

    timestamp: int
    traderData: str = ""
    listings: dict[str, ListingSchema] = {}
    order_depths: dict[str, OrderDepthSchema] = {}
    own_trades: dict[str, list[TradeStateSchema]] = {}
    market_trades: dict[str, list[TradeStateSchema]] = {}
    position: dict[str, int] = {}

    def to_trading_state(self) -> datamodel.TradingState:
        """Convert to a datamodel TradingState."""
        return datamodel.TradingState(
            timestamp=self.timestamp,
            traderData=self.traderData,
            listings={s: listing.to_datamodel() for s, listing in self.listings.items()},
            order_depths={s: od.to_datamodel() for s, od in self.order_depths.items()},
            own_trades={s: [t.to_datamodel() for t in tl] for s, tl in self.own_trades.items()},
            market_trades={
                s: [t.to_datamodel() for t in tl] for s, tl in self.market_trades.items()
            },
            position=dict(self.position),
            observations=datamodel.Observation(),
        )
