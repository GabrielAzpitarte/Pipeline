"""Golden tests for baseline strategies with locked expected results.

Each scenario uses synthetic BacktestData with carefully chosen market trades
to guarantee fills and produce exact known PnL values.
"""

from __future__ import annotations

import json
from pathlib import Path

from data.parse_logs import BacktestData, PriceRow, TradeRow
from sim.engine import SimConfig, SimEngine
from sim.matching import TradeMatchingMode

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
GOLDEN = json.loads((FIXTURES / "golden_baselines.json").read_text())


def _make_data(
    market_trades: list[TradeRow] | None = None,
) -> BacktestData:
    """Single-tick AMETHYSTS data with book 9998/10002 and optional market trades."""
    trades_by_ts: dict[int, dict[str, list[TradeRow]]] = {}
    if market_trades:
        trades_by_ts[100] = {"AMETHYSTS": market_trades}

    return BacktestData(
        timestamps=[100],
        prices={
            100: {
                "AMETHYSTS": PriceRow(
                    day=1,
                    timestamp=100,
                    product="AMETHYSTS",
                    bid_prices=[9998],
                    bid_volumes=[10],
                    ask_prices=[10002],
                    ask_volumes=[10],
                    mid_price=10000.0,
                    profit_loss=0.0,
                ),
            },
        },
        trades=trades_by_ts,
        products={"AMETHYSTS"},
    )


class TestGoldenMarketMaker:
    """Market maker with market trades at 9998 and 10002 gets both sides filled."""

    def test_both_sides_fill(self) -> None:
        expected = GOLDEN["market_maker_both_sides"]
        data = _make_data(
            market_trades=[
                TradeRow(1, 100, "bot_a", "bot_b", "AMETHYSTS", "SEASHELLS", 9998, 10),
                TradeRow(1, 100, "bot_c", "bot_d", "AMETHYSTS", "SEASHELLS", 10002, 10),
            ]
        )
        config = SimConfig(
            strategy_name=expected["strategy"],
            strategy_params=expected["params"],
            trade_match_mode=TradeMatchingMode.ALL,
        )
        result = SimEngine(config).run(data)

        assert len(result.all_fills) == expected["total_fills"]
        assert result.final_positions == expected["final_positions"]
        assert result.final_cash == expected["final_cash"]
        assert result.final_pnl == expected["final_pnl"]


class TestGoldenFairValue:
    """Fair value with market trades at 9997 and 10003 fills both sides."""

    def test_passive_fills(self) -> None:
        expected = GOLDEN["fair_value_passive"]
        data = _make_data(
            market_trades=[
                TradeRow(1, 100, "bot_a", "bot_b", "AMETHYSTS", "SEASHELLS", 9997, 10),
                TradeRow(1, 100, "bot_c", "bot_d", "AMETHYSTS", "SEASHELLS", 10003, 10),
            ]
        )
        config = SimConfig(
            strategy_name=expected["strategy"],
            strategy_params=expected["params"],
            trade_match_mode=TradeMatchingMode.ALL,
        )
        result = SimEngine(config).run(data)

        assert len(result.all_fills) == expected["total_fills"]
        assert result.final_positions == expected["final_positions"]
        assert result.final_cash == expected["final_cash"]
        assert result.final_pnl == expected["final_pnl"]


class TestGoldenInventoryMM:
    """Inventory MM at position 0 behaves like market maker (skew=0)."""

    def test_zero_position_same_as_mm(self) -> None:
        expected = GOLDEN["inventory_mm_zero_pos"]
        data = _make_data(
            market_trades=[
                TradeRow(1, 100, "bot_a", "bot_b", "AMETHYSTS", "SEASHELLS", 9998, 10),
                TradeRow(1, 100, "bot_c", "bot_d", "AMETHYSTS", "SEASHELLS", 10002, 10),
            ]
        )
        config = SimConfig(
            strategy_name=expected["strategy"],
            strategy_params=expected["params"],
            trade_match_mode=TradeMatchingMode.ALL,
        )
        result = SimEngine(config).run(data)

        assert len(result.all_fills) == expected["total_fills"]
        assert result.final_positions == expected["final_positions"]
        assert result.final_cash == expected["final_cash"]
        assert result.final_pnl == expected["final_pnl"]
