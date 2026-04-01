"""Basic tests for trader utilities."""

from trader.utils import mid_price, vwap


def test_mid_price() -> None:
    assert mid_price(100.0, 102.0) == 101.0


def test_vwap() -> None:
    result = vwap([100.0, 200.0], [10.0, 10.0])
    assert result == 150.0
