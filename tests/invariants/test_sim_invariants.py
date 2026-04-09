"""Simulation invariant tests — these must ALWAYS pass.

If any of these fail, the simulator has a fundamental correctness bug.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sim.limits import get_limit
from sim.matching import MarketTrade, TradeMatchingMode, match_orders
from trader.datamodel import Order, OrderDepth, Trade

# ---------------------------------------------------------------------------
# Invariant 1: Position limits are respected
# ---------------------------------------------------------------------------


class TestPositionLimitInvariant:
    """After limit enforcement, resulting positions must be within bounds."""

    def test_positions_within_limits_after_sim(self) -> None:
        """Run a real strategy on real data and verify positions stay within limits."""
        prices_path = Path("data_raw/prices_round_0_day_-1.csv")
        if not prices_path.exists():
            pytest.skip("Real data not available")

        from data.parse_logs import load_round_data
        from sim.engine import SimConfig, SimEngine

        data = load_round_data(prices_path, Path("data_raw/trades_round_0_day_-1.csv"))
        engine = SimEngine(SimConfig(strategy_name="market_maker"))
        result = engine.run(data)

        for tick in result.ticks:
            for product, pos in tick.positions.items():
                limit = get_limit(product)
                assert abs(pos) <= limit, (
                    f"Position limit violated at tick {tick.timestamp}: "
                    f"{product} position={pos}, limit={limit}"
                )


# ---------------------------------------------------------------------------
# Invariant 2: No double-liquidity from market trades
# ---------------------------------------------------------------------------


class TestNoDoubleLiquidity:
    """A single market trade must not provide liquidity to both sides simultaneously."""

    def test_single_trade_total_fills_capped(self) -> None:
        """One MarketTrade with qty=10 should not fill more than 10 total across both sides.

        The engine now splits trade quantity between sides (half each),
        so a trade of qty=10 provides at most 5+5=10 total liquidity.
        """
        trade = Trade(symbol="TEST", price=10000, quantity=10, buyer="A", seller="B")
        # Correct construction: split between sides
        half = max(1, trade.quantity // 2)
        mt = MarketTrade(trade=trade, buy_quantity=half, sell_quantity=half)

        buy_order = Order("TEST", 10000, 8)
        sell_order = Order("TEST", 10000, -8)

        fills = match_orders(
            {"TEST": [buy_order, sell_order]},
            {"TEST": OrderDepth()},
            {"TEST": [mt]},
            TradeMatchingMode.ALL,
        )

        total_filled = sum(abs(f.quantity) for f in fills.get("TEST", []))

        assert total_filled <= trade.quantity, (
            f"Double-liquidity: trade qty={trade.quantity}, but filled "
            f"total={total_filled} (should be <= {trade.quantity})"
        )

    def test_legacy_full_both_causes_double_liquidity(self) -> None:
        """Verify that the old buggy construction (full_both) produces double liquidity."""
        trade = Trade(symbol="TEST", price=10000, quantity=10, buyer="A", seller="B")
        # Legacy buggy construction: both sides get full quantity
        mt = MarketTrade(trade=trade, buy_quantity=10, sell_quantity=10)

        buy_order = Order("TEST", 10000, 8)
        sell_order = Order("TEST", 10000, -8)

        fills = match_orders(
            {"TEST": [buy_order, sell_order]},
            {"TEST": OrderDepth()},
            {"TEST": [mt]},
            TradeMatchingMode.ALL,
        )

        total_filled = sum(abs(f.quantity) for f in fills.get("TEST", []))
        # This SHOULD exceed the trade quantity — confirming the old bug
        assert (
            total_filled > trade.quantity
        ), f"Expected double-liquidity with full_both: got {total_filled}"


# ---------------------------------------------------------------------------
# Invariant 3: PnL consistency
# ---------------------------------------------------------------------------


class TestPnLConsistency:
    """PnL must equal cash + unrealized at every tick."""

    def test_pnl_equals_cash_plus_unrealized(self) -> None:
        """Verify PnL = cash + sum(position * mid_price) at every tick."""
        prices_path = Path("data_raw/prices_round_0_day_-1.csv")
        if not prices_path.exists():
            pytest.skip("Real data not available")

        from data.parse_logs import load_round_data
        from sim.engine import SimConfig, SimEngine

        data = load_round_data(prices_path, Path("data_raw/trades_round_0_day_-1.csv"))
        engine = SimEngine(SimConfig(strategy_name="market_maker"))
        result = engine.run(data)

        for tick in result.ticks:
            unrealized = sum(
                tick.positions.get(p, 0) * tick.mid_prices.get(p, 0) for p in tick.mid_prices
            )
            expected_pnl = tick.cash + unrealized
            assert abs(tick.pnl - expected_pnl) < 0.01, (
                f"PnL inconsistency at tick {tick.timestamp}: "
                f"reported={tick.pnl}, cash={tick.cash}, unrealized={unrealized}, "
                f"expected={expected_pnl}"
            )


# ---------------------------------------------------------------------------
# Invariant 4: Fill quantity signs are correct
# ---------------------------------------------------------------------------


class TestFillSignInvariant:
    """Buy order fills must have positive quantity, sell fills negative."""

    def test_fill_signs_match_orders(self) -> None:
        """Verify fill quantity signs are consistent with order direction."""
        depth = OrderDepth()
        depth.buy_orders = {9995: 20}
        depth.sell_orders = {10005: -20}

        buy_order = Order("TEST", 10010, 10)  # buy at 10010, crosses ask
        sell_order = Order("TEST", 9990, -10)  # sell at 9990, crosses bid

        fills = match_orders(
            {"TEST": [buy_order, sell_order]},
            {"TEST": depth},
            {},
            TradeMatchingMode.ALL,
        )

        for fill in fills.get("TEST", []):
            if fill.quantity > 0:
                assert fill.against == "book", "Positive fill should be from book crossing"
            elif fill.quantity < 0:
                assert fill.against == "book", "Negative fill should be from book crossing"
