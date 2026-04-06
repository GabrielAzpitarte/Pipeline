"""Tests for the Prosperity datamodel types."""

from __future__ import annotations

import json

from trader.datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    ProsperityEncoder,
    Trade,
    TradingState,
)


class TestOrder:
    def test_buy_order(self) -> None:
        o = Order("AMETHYSTS", 10000, 5)
        assert o.symbol == "AMETHYSTS"
        assert o.price == 10000
        assert o.quantity == 5

    def test_sell_order(self) -> None:
        o = Order("KELP", 2050, -3)
        assert o.quantity == -3

    def test_repr(self) -> None:
        o = Order("X", 100, 1)
        assert "X" in repr(o)


class TestOrderDepth:
    def test_empty(self) -> None:
        od = OrderDepth()
        assert od.buy_orders == {}
        assert od.sell_orders == {}

    def test_populated(self) -> None:
        od = OrderDepth()
        od.buy_orders = {9998: 10, 9996: 25}
        od.sell_orders = {10002: -10, 10004: -20}
        assert od.buy_orders[9998] == 10
        assert od.sell_orders[10002] == -10  # negative per convention


class TestTrade:
    def test_construction(self) -> None:
        t = Trade("KELP", 2050, 5, "alice", "bob", 100)
        assert t.symbol == "KELP"
        assert t.buyer == "alice"
        assert t.timestamp == 100

    def test_defaults(self) -> None:
        t = Trade("X", 100, 1)
        assert t.buyer == ""
        assert t.timestamp == 0


class TestTradingState:
    def test_construction(self) -> None:
        listing = Listing("A", "A", "SEASHELLS")
        state = TradingState(
            timestamp=100,
            traderData="",
            listings={"A": listing},
            order_depths={},
            own_trades={},
            market_trades={},
            position={"A": 5},
            observations=Observation(),
        )
        assert state.timestamp == 100
        assert state.position["A"] == 5
        assert state.traderData == ""

    def test_repr_contains_products(self) -> None:
        state = TradingState(
            timestamp=0,
            traderData="",
            listings={"X": Listing("X", "X", "S")},
            order_depths={},
            own_trades={},
            market_trades={},
            position={},
            observations=Observation(),
        )
        assert "X" in repr(state)


class TestProsperityEncoder:
    def test_encode_order(self) -> None:
        o = Order("A", 100, 5)
        result = json.loads(json.dumps(o, cls=ProsperityEncoder))
        assert result["symbol"] == "A"
        assert result["price"] == 100

    def test_encode_order_depth(self) -> None:
        od = OrderDepth()
        od.buy_orders = {100: 5}
        result = json.loads(json.dumps(od, cls=ProsperityEncoder))
        assert "buy_orders" in result

    def test_encode_trading_state(self) -> None:
        state = TradingState(
            timestamp=42,
            traderData="test",
            listings={},
            order_depths={},
            own_trades={},
            market_trades={},
            position={"A": 10},
            observations=Observation(),
        )
        result = json.loads(json.dumps(state, cls=ProsperityEncoder))
        assert result["timestamp"] == 42
        assert result["position"] == {"A": 10}
