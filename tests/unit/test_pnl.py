"""Tests for PnL tracking."""

from __future__ import annotations

from sim.pnl import PnLTracker


class TestRecordFill:
    def test_buy_decreases_cash(self) -> None:
        pnl = PnLTracker()
        pnl.record_fill("A", 100, 5)
        assert pnl.cash == -500  # paid 100 * 5
        assert pnl.positions["A"] == 5

    def test_sell_increases_cash(self) -> None:
        pnl = PnLTracker()
        pnl.record_fill("A", 100, -5)
        assert pnl.cash == 500  # received 100 * 5
        assert pnl.positions["A"] == -5

    def test_round_trip_profit(self) -> None:
        pnl = PnLTracker()
        pnl.record_fill("A", 100, 5)  # buy 5 @ 100
        pnl.record_fill("A", 105, -5)  # sell 5 @ 105
        assert pnl.cash == 25  # profit = 5 * (105 - 100) = 25
        assert pnl.positions["A"] == 0

    def test_round_trip_loss(self) -> None:
        pnl = PnLTracker()
        pnl.record_fill("A", 100, 5)  # buy 5 @ 100
        pnl.record_fill("A", 95, -5)  # sell 5 @ 95
        assert pnl.cash == -25  # loss = 5 * (95 - 100) = -25

    def test_multi_product(self) -> None:
        pnl = PnLTracker()
        pnl.record_fill("A", 100, 5)
        pnl.record_fill("B", 200, -3)
        assert pnl.positions["A"] == 5
        assert pnl.positions["B"] == -3
        assert pnl.cash_by_product["A"] == -500
        assert pnl.cash_by_product["B"] == 600


class TestUnrealizedPnl:
    def test_long_position(self) -> None:
        pnl = PnLTracker()
        pnl.record_fill("A", 100, 5)
        assert pnl.unrealized_pnl("A", 103.0) == 515.0

    def test_zero_position(self) -> None:
        pnl = PnLTracker()
        assert pnl.unrealized_pnl("A", 100.0) == 0.0


class TestTotalPnl:
    def test_cash_plus_unrealized(self) -> None:
        pnl = PnLTracker()
        pnl.record_fill("A", 100, 5)  # cash = -500
        # mid = 103 → unrealized = 5 * 103 = 515
        # total = -500 + 515 = 15
        assert pnl.total_pnl({"A": 103.0}) == 15.0

    def test_multi_product_total(self) -> None:
        pnl = PnLTracker()
        pnl.record_fill("A", 100, 5)  # cash_A = -500
        pnl.record_fill("B", 200, -3)  # cash_B = +600
        # total cash = 100
        # unrealized_A = 5 * 102 = 510, unrealized_B = -3 * 198 = -594
        # total = 100 + 510 - 594 = 16
        assert pnl.total_pnl({"A": 102.0, "B": 198.0}) == 16.0

    def test_total_realised_backward_compat(self) -> None:
        pnl = PnLTracker()
        pnl.record_fill("A", 100, 5)
        pnl.record_fill("A", 105, -5)
        assert pnl.total_realised() == 25.0
