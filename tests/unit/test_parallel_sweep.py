"""Tests for parallel sweep functionality in experiments/sweep_runner.py."""

from __future__ import annotations

from pathlib import Path

from experiments.sweep_runner import (
    _apply_params_to_source,
    _make_trader_from_source,
    export_sweep_winners,
    run_sweep_parallel,
)

# Minimal strategy source using module-level constants
_CONST_STRATEGY = """\
BASE_SIZE = 15
EDGE = 2

class Listing:
    def __init__(self, symbol, product, denomination):
        self.symbol = symbol; self.product = product; self.denomination = denomination

class Order:
    def __init__(self, symbol, price, quantity):
        self.symbol = symbol; self.price = price; self.quantity = quantity

class OrderDepth:
    def __init__(self):
        self.buy_orders = {}; self.sell_orders = {}

class Trade:
    def __init__(self, symbol, price, quantity, buyer="", seller="", timestamp=0):
        self.symbol = symbol; self.price = price; self.quantity = quantity
        self.buyer = buyer; self.seller = seller; self.timestamp = timestamp

class Observation:
    def __init__(self, plainValueObservations=None, conversionObservations=None):
        self.plainValueObservations = plainValueObservations or {}
        self.conversionObservations = conversionObservations or {}

class TradingState:
    def __init__(self, timestamp, traderData, listings, order_depths, own_trades,
                 market_trades, position, observations):
        self.timestamp = timestamp; self.traderData = traderData
        self.listings = listings; self.order_depths = order_depths
        self.own_trades = own_trades; self.market_trades = market_trades
        self.position = position; self.observations = observations

class Trader:
    def __init__(self):
        pass
    def run(self, state):
        orders = {}
        for sym, depth in state.order_depths.items():
            if not depth.buy_orders or not depth.sell_orders:
                continue
            bb = max(depth.buy_orders.keys())
            ba = min(depth.sell_orders.keys())
            orders[sym] = [
                Order(sym, bb + 1, BASE_SIZE),
                Order(sym, ba - 1, -BASE_SIZE),
            ]
        return orders, 0, ""
"""

# Minimal strategy using p.get() pattern
_PGET_STRATEGY = """\
class Listing:
    def __init__(self, symbol, product, denomination):
        self.symbol = symbol; self.product = product; self.denomination = denomination

class Order:
    def __init__(self, symbol, price, quantity):
        self.symbol = symbol; self.price = price; self.quantity = quantity

class OrderDepth:
    def __init__(self):
        self.buy_orders = {}; self.sell_orders = {}

class Trade:
    def __init__(self, symbol, price, quantity, buyer="", seller="", timestamp=0):
        self.symbol = symbol; self.price = price; self.quantity = quantity
        self.buyer = buyer; self.seller = seller; self.timestamp = timestamp

class Observation:
    def __init__(self, plainValueObservations=None, conversionObservations=None):
        self.plainValueObservations = plainValueObservations or {}
        self.conversionObservations = conversionObservations or {}

class TradingState:
    def __init__(self, timestamp, traderData, listings, order_depths, own_trades,
                 market_trades, position, observations):
        self.timestamp = timestamp; self.traderData = traderData
        self.listings = listings; self.order_depths = order_depths
        self.own_trades = own_trades; self.market_trades = market_trades
        self.position = position; self.observations = observations

class Trader:
    def __init__(self, params=None):
        p = params or {}
        self.size = int(p.get("size", 10))
    def run(self, state):
        orders = {}
        for sym, depth in state.order_depths.items():
            if not depth.buy_orders or not depth.sell_orders:
                continue
            bb = max(depth.buy_orders.keys())
            ba = min(depth.sell_orders.keys())
            orders[sym] = [
                Order(sym, bb + 1, self.size),
                Order(sym, ba - 1, -self.size),
            ]
        return orders, 0, ""
"""


class TestApplyParamsToSource:
    def test_module_constant(self) -> None:
        result = _apply_params_to_source(_CONST_STRATEGY, {"BASE_SIZE": 20})
        assert "BASE_SIZE = 20" in result
        assert "BASE_SIZE = 15" not in result

    def test_pget_pattern(self) -> None:
        result = _apply_params_to_source(_PGET_STRATEGY, {"size": 25})
        assert 'p.get("size", 25)' in result
        assert 'p.get("size", 10)' not in result

    def test_multiple_overrides(self) -> None:
        result = _apply_params_to_source(_CONST_STRATEGY, {"BASE_SIZE": 20, "EDGE": 5})
        assert "BASE_SIZE = 20" in result
        assert "EDGE = 5" in result

    def test_no_match_is_noop(self) -> None:
        result = _apply_params_to_source(_CONST_STRATEGY, {"NONEXISTENT": 99})
        assert result == _CONST_STRATEGY


class TestMakeTraderFromSource:
    def test_returns_trader_class(self) -> None:
        cls = _make_trader_from_source(_CONST_STRATEGY)
        assert cls.__name__ == "Trader"

    def test_trader_is_instantiable(self) -> None:
        cls = _make_trader_from_source(_CONST_STRATEGY)
        trader = cls()
        assert trader is not None

    def test_missing_trader_raises(self) -> None:
        import pytest

        with pytest.raises(RuntimeError, match="does not define a Trader"):
            _make_trader_from_source("x = 1")


class TestRunSweepParallel:
    def test_basic_sweep(self) -> None:
        from data.parse_logs import load_round_data

        data = load_round_data(
            Path("tests/fixtures/sample_prices.csv"),
            Path("tests/fixtures/sample_trades.csv"),
        )
        results = run_sweep_parallel(
            strategy_source=_CONST_STRATEGY,
            param_grid={"BASE_SIZE": [10, 15]},
            data=data,
            max_workers=2,
        )
        assert len(results) == 2
        # Results should be sorted by total_pnl descending
        assert results[0][1]["total_pnl"] >= results[1][1]["total_pnl"]

    def test_full_grid_count(self) -> None:
        from data.parse_logs import load_round_data

        data = load_round_data(
            Path("tests/fixtures/sample_prices.csv"),
            Path("tests/fixtures/sample_trades.csv"),
        )
        results = run_sweep_parallel(
            strategy_source=_CONST_STRATEGY,
            param_grid={"BASE_SIZE": [10, 15], "EDGE": [1, 2, 3]},
            data=data,
            max_workers=2,
        )
        assert len(results) == 6  # 2 x 3 full Cartesian product

    def test_results_contain_metrics(self) -> None:
        from data.parse_logs import load_round_data

        data = load_round_data(
            Path("tests/fixtures/sample_prices.csv"),
            Path("tests/fixtures/sample_trades.csv"),
        )
        results = run_sweep_parallel(
            strategy_source=_CONST_STRATEGY,
            param_grid={"BASE_SIZE": [15]},
            data=data,
            max_workers=1,
        )
        params, metrics = results[0]
        assert "total_pnl" in metrics
        assert "total_fills" in metrics
        assert params == {"BASE_SIZE": 15}


class TestExportSweepWinners:
    def test_creates_files(self, tmp_path: Path) -> None:
        results = [
            ({"BASE_SIZE": 10}, {"total_pnl": 1000.0}),
            ({"BASE_SIZE": 15}, {"total_pnl": 900.0}),
            ({"BASE_SIZE": 20}, {"total_pnl": 800.0}),
        ]
        paths = export_sweep_winners(_CONST_STRATEGY, results, tmp_path, top_n=3)
        assert len(paths) == 3
        for p in paths:
            assert p.exists()
            content = p.read_text()
            assert "class Trader" in content

    def test_applies_params(self, tmp_path: Path) -> None:
        results = [({"BASE_SIZE": 42}, {"total_pnl": 5000.0})]
        paths = export_sweep_winners(_CONST_STRATEGY, results, tmp_path, top_n=1)
        content = paths[0].read_text()
        assert "BASE_SIZE = 42" in content

    def test_top_n_limits(self, tmp_path: Path) -> None:
        results = [({"BASE_SIZE": i}, {"total_pnl": float(i)}) for i in range(10)]
        paths = export_sweep_winners(_CONST_STRATEGY, results, tmp_path, top_n=2)
        assert len(paths) == 2
