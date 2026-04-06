"""Basic tests for trader utilities."""

from trader.datamodel import OrderDepth
from trader.utils import best_ask, best_bid, mid_price, mid_price_from_depth, vwap


def test_mid_price() -> None:
    assert mid_price(100.0, 102.0) == 101.0


def test_vwap() -> None:
    result = vwap([100.0, 200.0], [10.0, 10.0])
    assert result == 150.0


class TestOrderDepthHelpers:
    def test_best_bid(self) -> None:
        od = OrderDepth()
        od.buy_orders = {9998: 10, 9996: 25, 9994: 15}
        assert best_bid(od) == 9998

    def test_best_bid_empty(self) -> None:
        assert best_bid(OrderDepth()) is None

    def test_best_ask(self) -> None:
        od = OrderDepth()
        od.sell_orders = {10002: -10, 10004: -20}
        assert best_ask(od) == 10002

    def test_best_ask_empty(self) -> None:
        assert best_ask(OrderDepth()) is None

    def test_mid_price_from_depth(self) -> None:
        od = OrderDepth()
        od.buy_orders = {9998: 10}
        od.sell_orders = {10002: -10}
        assert mid_price_from_depth(od) == 10000.0

    def test_mid_price_from_depth_empty(self) -> None:
        assert mid_price_from_depth(OrderDepth()) is None
