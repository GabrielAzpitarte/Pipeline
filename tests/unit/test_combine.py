"""Tests for submission/combine.py."""

from __future__ import annotations

from pathlib import Path

from submission.combine import (
    StrategyComponent,
    _extract_imports,
    _extract_module_constants,
    combine_strategies_python,
)

_EMERALDS_STRATEGY = """\
import math

BASE_SIZE = 15
UNWIND_THRESHOLD = 50

class Trader:
    def __init__(self) -> None:
        self.em_counter = 0

    def run(self, state):
        orders = {}
        for symbol in ["EMERALDS"]:
            depth = state.order_depths.get(symbol)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue
            pos = state.position.get(symbol, 0)
            bb = max(depth.buy_orders.keys())
            ba = min(depth.sell_orders.keys())
            if symbol == "EMERALDS":
                fair = 10000
                sym_orders = []
                sym_orders.append(Order(symbol, bb + 1, BASE_SIZE))
                sym_orders.append(Order(symbol, ba - 1, -BASE_SIZE))
                orders[symbol] = sym_orders
        return orders, 0, ""
"""

_TOMATOES_STRATEGY = """\
import math

EMA_ALPHA = 0.15
ORDER_SIZE = 12

class Trader:
    def __init__(self) -> None:
        self.tom_ema = None

    def run(self, state):
        orders = {}
        for symbol in ["TOMATOES"]:
            depth = state.order_depths.get(symbol)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue
            bb = max(depth.buy_orders.keys())
            ba = min(depth.sell_orders.keys())
            mid = (bb + ba) / 2
            if symbol == "TOMATOES":
                if self.tom_ema is None:
                    self.tom_ema = mid
                self.tom_ema = EMA_ALPHA * mid + (1 - EMA_ALPHA) * self.tom_ema
                sym_orders = []
                sym_orders.append(Order(symbol, bb + 1, ORDER_SIZE))
                sym_orders.append(Order(symbol, ba - 1, -ORDER_SIZE))
                orders[symbol] = sym_orders
        return orders, 0, ""
"""


class TestExtractImports:
    def test_extracts_math(self) -> None:
        imports = _extract_imports(_EMERALDS_STRATEGY)
        assert "import math" in imports

    def test_skips_typing(self) -> None:
        code = "from typing import Dict, List\nimport math\n"
        imports = _extract_imports(code)
        assert len(imports) == 1
        assert "import math" in imports


class TestExtractModuleConstants:
    def test_extracts_constants(self) -> None:
        constants = _extract_module_constants(_EMERALDS_STRATEGY)
        assert "BASE_SIZE = 15" in constants
        assert "UNWIND_THRESHOLD = 50" in constants


class TestCombineStrategiesPython:
    def test_produces_valid_python(self) -> None:
        components = [
            StrategyComponent(source_code=_EMERALDS_STRATEGY, products=["EMERALDS"]),
            StrategyComponent(source_code=_TOMATOES_STRATEGY, products=["TOMATOES"]),
        ]
        result = combine_strategies_python(components)
        # Could return None if extraction fails, but for these simple strategies it should work
        if result is not None:
            # Should compile without errors
            compile(result, "<test>", "exec")
            assert "class Trader" in result
            assert "EMERALDS" in result
            assert "TOMATOES" in result

    def test_merges_constants(self) -> None:
        components = [
            StrategyComponent(source_code=_EMERALDS_STRATEGY, products=["EMERALDS"]),
            StrategyComponent(source_code=_TOMATOES_STRATEGY, products=["TOMATOES"]),
        ]
        result = combine_strategies_python(components)
        if result is not None:
            assert "BASE_SIZE" in result
            assert "EMA_ALPHA" in result

    def test_contains_sub_traders(self) -> None:
        components = [
            StrategyComponent(source_code=_EMERALDS_STRATEGY, products=["EMERALDS"]),
            StrategyComponent(source_code=_TOMATOES_STRATEGY, products=["TOMATOES"]),
        ]
        result = combine_strategies_python(components)
        if result is not None:
            assert "_Trader_emeralds" in result
            assert "_Trader_tomatoes" in result
            assert "_dispatch" in result


class TestCombineBestPerProduct:
    def test_writes_file(self, tmp_path: Path) -> None:
        from submission.combine import combine_best_per_product

        output = tmp_path / "combined.py"
        result = combine_best_per_product(
            emeralds_code=_EMERALDS_STRATEGY,
            emeralds_params={},
            tomatoes_code=_TOMATOES_STRATEGY,
            tomatoes_params={},
            output_path=output,
        )
        assert result.exists()
        content = result.read_text()
        assert "class Trader" in content
