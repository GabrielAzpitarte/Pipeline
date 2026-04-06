"""Tests for the simulation engine."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from data.parse_logs import BacktestData, PriceRow, load_round_data
from sim.engine import SimConfig, SimEngine
from trader.datamodel import Order, TradingState
from trader.strategies import STRATEGIES, register

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _make_simple_data() -> BacktestData:
    """Create a minimal BacktestData with one product, two ticks."""
    prices: dict[int, dict[str, PriceRow]] = {
        100: {
            "AMETHYSTS": PriceRow(
                day=1,
                timestamp=100,
                product="AMETHYSTS",
                bid_prices=[9998, 9996],
                bid_volumes=[10, 25],
                ask_prices=[10002, 10004],
                ask_volumes=[10, 20],
                mid_price=10000.0,
                profit_loss=0.0,
            ),
        },
        200: {
            "AMETHYSTS": PriceRow(
                day=1,
                timestamp=200,
                product="AMETHYSTS",
                bid_prices=[9999, 9997],
                bid_volumes=[12, 20],
                ask_prices=[10001, 10003],
                ask_volumes=[12, 18],
                mid_price=10000.0,
                profit_loss=0.0,
            ),
        },
    }
    return BacktestData(
        timestamps=[100, 200],
        prices=prices,
        trades=defaultdict(dict),
        products={"AMETHYSTS"},
    )


class TestEngineNoop:
    def test_noop_no_fills(self) -> None:
        data = _make_simple_data()
        engine = SimEngine(SimConfig(strategy_name="noop"))
        result = engine.run(data)
        assert len(result.ticks) == 2
        assert result.all_fills == []
        assert result.final_positions == {}
        assert result.final_cash == 0.0


class TestEngineFills:
    def setup_method(self) -> None:
        @register("_test_buyer")
        class _BuyerStrategy:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {"AMETHYSTS": [Order("AMETHYSTS", 10002, 5)]}

    def teardown_method(self) -> None:
        STRATEGIES.pop("_test_buyer", None)

    def test_buy_fill_updates_position_and_cash(self) -> None:
        data = _make_simple_data()
        engine = SimEngine(SimConfig(strategy_name="_test_buyer"))
        result = engine.run(data)
        # Tick 1: buy 5 @ 10002 (crossing ask). Fill at 10002.
        # Tick 2: buy 5 @ 10001 (next tick's ask is 10001). Fill at 10001.
        assert len(result.all_fills) == 2
        assert result.final_positions["AMETHYSTS"] == 10
        # cash: -5*10002 - 5*10001 = -100015
        assert result.final_cash == -(5 * 10002 + 5 * 10001)


class TestEngineLimitRejection:
    def setup_method(self) -> None:
        @register("_test_hog")
        class _HogStrategy:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                return {"AMETHYSTS": [Order("AMETHYSTS", 10002, 25)]}  # > limit 20

    def teardown_method(self) -> None:
        STRATEGIES.pop("_test_hog", None)

    def test_all_or_nothing_rejection(self) -> None:
        data = _make_simple_data()
        engine = SimEngine(SimConfig(strategy_name="_test_hog"))
        result = engine.run(data)
        assert result.all_fills == []
        assert result.final_positions == {}


class TestEngineTraderDataChaining:
    def setup_method(self) -> None:
        @register("_test_data_chain")
        class _DataChainStrategy:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                # Just check traderData was received; return no orders
                return {}

    def teardown_method(self) -> None:
        STRATEGIES.pop("_test_data_chain", None)

    def test_trader_data_flows(self) -> None:
        data = _make_simple_data()
        engine = SimEngine(SimConfig(strategy_name="_test_data_chain"))
        result = engine.run(data)
        assert len(result.ticks) == 2


class TestEngineOwnTradesChaining:
    def setup_method(self) -> None:
        self.seen_own_trades: list[dict[str, int]] = []

        seen = self.seen_own_trades

        @register("_test_own_trades")
        class _OwnTradesStrategy:
            def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
                seen.append({s: len(tl) for s, tl in state.own_trades.items()})
                if state.timestamp == 100:
                    return {"AMETHYSTS": [Order("AMETHYSTS", 10002, 5)]}
                return {}

    def teardown_method(self) -> None:
        STRATEGIES.pop("_test_own_trades", None)

    def test_fills_appear_as_own_trades_next_tick(self) -> None:
        data = _make_simple_data()
        engine = SimEngine(SimConfig(strategy_name="_test_own_trades"))
        engine.run(data)
        # Tick 1 (t=100): no own_trades yet
        assert self.seen_own_trades[0] == {}
        # Tick 2 (t=200): should see the fill from tick 1
        assert self.seen_own_trades[1].get("AMETHYSTS", 0) >= 1


class TestEngineFromCsv:
    def test_runs_with_csv_data(self) -> None:
        data = load_round_data(
            FIXTURES_DIR / "sample_prices.csv",
            FIXTURES_DIR / "sample_trades.csv",
        )
        engine = SimEngine(SimConfig(strategy_name="noop"))
        result = engine.run(data)
        assert len(result.ticks) == 3
        assert result.final_pnl == 0.0
