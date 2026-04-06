"""Golden tests for backtester scenarios with locked expected results."""

from __future__ import annotations

from collections import defaultdict

from data.parse_logs import BacktestData, PriceRow
from sim.engine import SimConfig, SimEngine
from trader.datamodel import Order, TradingState
from trader.strategies import STRATEGIES, register


def _one_tick_data(
    product: str,
    bid_prices: list[int],
    bid_volumes: list[int],
    ask_prices: list[int],
    ask_volumes: list[int],
    mid_price: float,
) -> BacktestData:
    """Create BacktestData with a single product and single tick."""
    return BacktestData(
        timestamps=[100],
        prices={
            100: {
                product: PriceRow(
                    day=1,
                    timestamp=100,
                    product=product,
                    bid_prices=bid_prices,
                    bid_volumes=bid_volumes,
                    ask_prices=ask_prices,
                    ask_volumes=ask_volumes,
                    mid_price=mid_price,
                    profit_loss=0.0,
                ),
            },
        },
        trades=defaultdict(dict),
        products={product},
    )


class TestGoldenAggressiveTaker:
    """Buy order crosses the spread — fills at the ask price, not the order price."""

    def setup_method(self) -> None:
        @register("_golden_taker")
        class _TakerStrategy:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {"AMETHYSTS": [Order("AMETHYSTS", 10005, 5)]}

    def teardown_method(self) -> None:
        STRATEGIES.pop("_golden_taker", None)

    def test_fill_price_is_ask_not_order(self) -> None:
        data = _one_tick_data(
            "AMETHYSTS",
            bid_prices=[9998],
            bid_volumes=[10],
            ask_prices=[10002],
            ask_volumes=[10],
            mid_price=10000.0,
        )
        engine = SimEngine(SimConfig(strategy_name="_golden_taker"))
        result = engine.run(data)
        assert len(result.all_fills) == 1
        fill = result.all_fills[0]
        assert fill.price == 10002  # ask price, not 10005
        assert fill.quantity == 5
        assert result.final_positions["AMETHYSTS"] == 5
        # cash = -5 * 10002 = -50010
        assert result.final_cash == -50010
        # pnl = cash + unrealized = -50010 + 5 * 10000 = -10
        assert result.final_pnl == -10.0


class TestGoldenPositionLimitBlock:
    """Orders exceeding position limits are fully rejected."""

    def setup_method(self) -> None:
        @register("_golden_overlimit")
        class _OverLimitStrategy:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {"AMETHYSTS": [Order("AMETHYSTS", 10002, 21)]}  # limit is 20

    def teardown_method(self) -> None:
        STRATEGIES.pop("_golden_overlimit", None)

    def test_no_fills_when_over_limit(self) -> None:
        data = _one_tick_data(
            "AMETHYSTS",
            bid_prices=[9998],
            bid_volumes=[30],
            ask_prices=[10002],
            ask_volumes=[30],
            mid_price=10000.0,
        )
        engine = SimEngine(SimConfig(strategy_name="_golden_overlimit"))
        result = engine.run(data)
        assert result.all_fills == []
        assert result.final_positions == {}
        assert result.final_cash == 0.0
        assert result.final_pnl == 0.0


class TestGoldenMultiLevelSweep:
    """Buy order sweeps multiple ask levels."""

    def setup_method(self) -> None:
        @register("_golden_sweep")
        class _SweepStrategy:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {"AMETHYSTS": [Order("AMETHYSTS", 10006, 15)]}

    def teardown_method(self) -> None:
        STRATEGIES.pop("_golden_sweep", None)

    def test_fills_at_each_level(self) -> None:
        data = _one_tick_data(
            "AMETHYSTS",
            bid_prices=[9998],
            bid_volumes=[10],
            ask_prices=[10002, 10004, 10006],
            ask_volumes=[5, 5, 10],
            mid_price=10000.0,
        )
        engine = SimEngine(SimConfig(strategy_name="_golden_sweep"))
        result = engine.run(data)
        assert len(result.all_fills) == 3
        assert result.all_fills[0].price == 10002
        assert result.all_fills[0].quantity == 5
        assert result.all_fills[1].price == 10004
        assert result.all_fills[1].quantity == 5
        assert result.all_fills[2].price == 10006
        assert result.all_fills[2].quantity == 5
        assert result.final_positions["AMETHYSTS"] == 15
        expected_cash = -(5 * 10002 + 5 * 10004 + 5 * 10006)
        assert result.final_cash == expected_cash
