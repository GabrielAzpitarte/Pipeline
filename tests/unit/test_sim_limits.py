"""Tests for all-or-nothing position limit enforcement."""

from __future__ import annotations

from sim.limits import enforce_limits
from trader.datamodel import Order


class TestEnforceLimits:
    def test_within_limit_accepted(self) -> None:
        orders = {"AMETHYSTS": [Order("AMETHYSTS", 10000, 5)]}
        result = enforce_limits(orders, positions={})
        assert "AMETHYSTS" in result
        assert len(result["AMETHYSTS"]) == 1

    def test_buy_exceeds_limit_all_rejected(self) -> None:
        orders = {
            "AMETHYSTS": [
                Order("AMETHYSTS", 10000, 10),
                Order("AMETHYSTS", 10001, 15),  # total buy = 25 > 20
            ]
        }
        result = enforce_limits(orders, positions={})
        assert "AMETHYSTS" not in result

    def test_sell_exceeds_limit_all_rejected(self) -> None:
        orders = {
            "AMETHYSTS": [
                Order("AMETHYSTS", 10000, -10),
                Order("AMETHYSTS", 9999, -15),  # total sell = -25, pos = -25, |25| > 20
            ]
        }
        result = enforce_limits(orders, positions={})
        assert "AMETHYSTS" not in result

    def test_mixed_buy_sell_within_limits(self) -> None:
        orders = {
            "AMETHYSTS": [
                Order("AMETHYSTS", 10000, 10),  # buy 10
                Order("AMETHYSTS", 10002, -10),  # sell 10
            ]
        }
        # max_long = 0 + 10 = 10 <= 20, max_short = 0 + (-10) = -10, |-10| <= 20
        result = enforce_limits(orders, positions={})
        assert "AMETHYSTS" in result

    def test_existing_position_near_limit(self) -> None:
        orders = {"AMETHYSTS": [Order("AMETHYSTS", 10000, 5)]}
        result = enforce_limits(orders, positions={"AMETHYSTS": 18})
        # max_long = 18 + 5 = 23 > 20 → rejected
        assert "AMETHYSTS" not in result

    def test_mixed_symbols_only_violator_rejected(self) -> None:
        orders = {
            "AMETHYSTS": [Order("AMETHYSTS", 10000, 25)],  # > 20
            "KELP": [Order("KELP", 2050, 5)],  # fine
        }
        result = enforce_limits(orders, positions={})
        assert "AMETHYSTS" not in result
        assert "KELP" in result

    def test_exactly_at_limit_accepted(self) -> None:
        orders = {"AMETHYSTS": [Order("AMETHYSTS", 10000, 20)]}
        result = enforce_limits(orders, positions={})
        assert "AMETHYSTS" in result

    def test_one_over_limit_rejected(self) -> None:
        orders = {"AMETHYSTS": [Order("AMETHYSTS", 10000, 21)]}
        result = enforce_limits(orders, positions={})
        assert "AMETHYSTS" not in result

    def test_empty_orders(self) -> None:
        result = enforce_limits({}, positions={})
        assert result == {}

    def test_short_symmetry(self) -> None:
        orders = {"AMETHYSTS": [Order("AMETHYSTS", 10000, -20)]}
        result = enforce_limits(orders, positions={})
        # max_short = 0 + (-20) = -20, |-20| = 20 <= 20
        assert "AMETHYSTS" in result
