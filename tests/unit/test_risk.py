"""Tests for risk validation."""

from __future__ import annotations

from trader.datamodel import Order
from trader.risk import RiskLimits, check_order, validate_orders


class TestCheckOrder:
    def test_order_passes(self) -> None:
        o = Order("AMETHYSTS", 10000, 5)
        assert check_order(o, current_position=0, product_limit=20) is True

    def test_order_exceeds_max_order_size(self) -> None:
        o = Order("AMETHYSTS", 10000, 15)
        limits = RiskLimits(max_order_size=10)
        assert check_order(o, current_position=0, product_limit=20, limits=limits) is False

    def test_order_breaches_position_limit(self) -> None:
        o = Order("AMETHYSTS", 10000, 10)
        assert check_order(o, current_position=15, product_limit=20) is False

    def test_sell_order_passes(self) -> None:
        o = Order("AMETHYSTS", 10000, -5)
        assert check_order(o, current_position=10, product_limit=20) is True

    def test_sell_exceeds_negative_limit(self) -> None:
        o = Order("AMETHYSTS", 10000, -10)
        assert check_order(o, current_position=-15, product_limit=20) is False


class TestValidateOrders:
    def test_all_pass(self) -> None:
        orders = {
            "AMETHYSTS": [Order("AMETHYSTS", 10000, 5), Order("AMETHYSTS", 9999, 3)],
        }
        result = validate_orders(orders, positions={}, limits=RiskLimits(max_order_size=20))
        assert len(result["AMETHYSTS"]) == 2

    def test_cumulative_position_tracking(self) -> None:
        orders = {
            "AMETHYSTS": [
                Order("AMETHYSTS", 10000, 10),
                Order("AMETHYSTS", 9999, 10),
                Order("AMETHYSTS", 9998, 5),
            ],
        }
        result = validate_orders(orders, positions={}, limits=RiskLimits(max_order_size=20))
        # pos starts at 0; +10=10 ok, +10=20 ok, +5=25 rejected (limit=20)
        assert len(result["AMETHYSTS"]) == 2

    def test_empty_positions_defaults_to_zero(self) -> None:
        orders = {"KELP": [Order("KELP", 2050, 5)]}
        result = validate_orders(orders, positions={}, limits=RiskLimits(max_order_size=20))
        assert len(result["KELP"]) == 1

    def test_filters_across_products(self) -> None:
        orders = {
            "AMETHYSTS": [Order("AMETHYSTS", 10000, 5)],
            "KELP": [Order("KELP", 2050, 100)],  # exceeds order size
        }
        result = validate_orders(orders, positions={}, limits=RiskLimits(max_order_size=10))
        assert "AMETHYSTS" in result
        assert "KELP" not in result  # all orders rejected, key excluded

    def test_empty_input(self) -> None:
        result = validate_orders({}, positions={})
        assert result == {}
