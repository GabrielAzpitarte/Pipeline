"""Tests for pydantic schemas and TradingState deserialization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from data.schemas import (
    ListingSchema,
    OrderDepthSchema,
    TradeStateSchema,
    TradingStateSchema,
)
from trader.datamodel import Listing, OrderDepth, Trade, TradingState

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class TestListingSchema:
    def test_to_datamodel(self) -> None:
        ls = ListingSchema(symbol="A", product="A", denomination="SEASHELLS")
        dm = ls.to_datamodel()
        assert isinstance(dm, Listing)
        assert dm.symbol == "A"

    def test_default_denomination(self) -> None:
        ls = ListingSchema(symbol="A", product="A")
        assert ls.denomination == "SEASHELLS"


class TestOrderDepthSchema:
    def test_to_datamodel(self) -> None:
        ods = OrderDepthSchema(
            buy_orders={"9998": 10, "9996": 25},
            sell_orders={"10002": -10},
        )
        od = ods.to_datamodel()
        assert isinstance(od, OrderDepth)
        assert od.buy_orders[9998] == 10
        assert od.sell_orders[10002] == -10

    def test_empty(self) -> None:
        ods = OrderDepthSchema()
        od = ods.to_datamodel()
        assert od.buy_orders == {}
        assert od.sell_orders == {}


class TestTradeStateSchema:
    def test_to_datamodel(self) -> None:
        ts = TradeStateSchema(
            symbol="X", price=100, quantity=5, buyer="a", seller="b", timestamp=10
        )
        t = ts.to_datamodel()
        assert isinstance(t, Trade)
        assert t.price == 100
        assert t.buyer == "a"


class TestTradingStateSchema:
    def test_from_json_file(self) -> None:
        raw = json.loads((FIXTURES_DIR / "sample_states.json").read_text())
        state_schema = TradingStateSchema.model_validate(raw[0])
        state = state_schema.to_trading_state()
        assert isinstance(state, TradingState)
        assert state.timestamp == 100
        assert "RAINFOREST_RESIN" in state.listings
        assert 9998 in state.order_depths["RAINFOREST_RESIN"].buy_orders

    def test_all_fixtures_parse(self) -> None:
        raw = json.loads((FIXTURES_DIR / "sample_states.json").read_text())
        for entry in raw:
            schema = TradingStateSchema.model_validate(entry)
            state = schema.to_trading_state()
            assert isinstance(state, TradingState)

    def test_missing_optional_fields(self) -> None:
        minimal = {"timestamp": 0}
        schema = TradingStateSchema.model_validate(minimal)
        state = schema.to_trading_state()
        assert state.timestamp == 0
        assert state.traderData == ""
        assert state.position == {}

    def test_invalid_timestamp_raises(self) -> None:
        with pytest.raises(ValidationError):
            TradingStateSchema.model_validate({"timestamp": "not_a_number"})
