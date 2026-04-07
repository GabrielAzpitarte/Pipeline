"""Tests for param extraction and grid generation in agents/tools/strategy_tools.py."""

from __future__ import annotations

from agents.tools.strategy_tools import (
    apply_params_to_code,
    extract_all_params,
    extract_module_constants,
    generate_sweep_grid,
)

_MODULE_CONST_CODE = """\
BASE_SIZE = 15
SKEW_FACTOR = 0.5
EMA_ALPHA = 0.15
UNWIND_THRESHOLD = 50
SOME_STRING = "hello"

class Trader:
    pass
"""

_PGET_CODE = """\
class Trader:
    def __init__(self, params=None):
        p = params or {}
        self.size = int(p.get("size", 10))
        self.alpha = float(p.get("alpha", 0.2))
        self.name = p.get("name", "default")
"""


class TestExtractModuleConstants:
    def test_extracts_int_constants(self) -> None:
        result = extract_module_constants(_MODULE_CONST_CODE)
        assert result["BASE_SIZE"] == 15
        assert result["UNWIND_THRESHOLD"] == 50
        assert isinstance(result["BASE_SIZE"], int)

    def test_extracts_float_constants(self) -> None:
        result = extract_module_constants(_MODULE_CONST_CODE)
        assert result["SKEW_FACTOR"] == 0.5
        assert result["EMA_ALPHA"] == 0.15
        assert isinstance(result["SKEW_FACTOR"], float)

    def test_skips_string_constants(self) -> None:
        result = extract_module_constants(_MODULE_CONST_CODE)
        assert "SOME_STRING" not in result

    def test_empty_code(self) -> None:
        assert extract_module_constants("") == {}

    def test_no_constants(self) -> None:
        assert extract_module_constants("x = 1\ny = 2\n") == {}


class TestExtractAllParams:
    def test_module_constants(self) -> None:
        result = extract_all_params(_MODULE_CONST_CODE)
        assert "BASE_SIZE" in result
        assert "SKEW_FACTOR" in result

    def test_pget_params(self) -> None:
        result = extract_all_params(_PGET_CODE)
        assert result["size"] == 10
        assert result["alpha"] == 0.2
        # String params should be skipped
        assert "name" not in result

    def test_combined(self) -> None:
        combined = _MODULE_CONST_CODE + "\n" + _PGET_CODE
        result = extract_all_params(combined)
        assert "BASE_SIZE" in result
        assert "size" in result


class TestGenerateSweepGrid:
    def test_three_values(self) -> None:
        grid = generate_sweep_grid({"x": 10}, n_values=3)
        assert len(grid["x"]) == 3

    def test_five_values(self) -> None:
        grid = generate_sweep_grid({"x": 10.0}, n_values=5)
        assert len(grid["x"]) == 5

    def test_default_included(self) -> None:
        grid = generate_sweep_grid({"x": 10}, n_values=3)
        assert 10 in grid["x"]

    def test_int_stays_int(self) -> None:
        grid = generate_sweep_grid({"x": 10}, n_values=3)
        for v in grid["x"]:
            assert isinstance(v, int)

    def test_float_stays_float(self) -> None:
        grid = generate_sweep_grid({"x": 0.5}, n_values=3)
        for v in grid["x"]:
            assert isinstance(v, float)

    def test_zero_default(self) -> None:
        grid = generate_sweep_grid({"x": 0}, n_values=3)
        assert 0 in grid["x"]
        assert len(grid["x"]) == 3

    def test_multiple_params(self) -> None:
        grid = generate_sweep_grid({"a": 10, "b": 0.5}, n_values=3)
        assert "a" in grid
        assert "b" in grid


class TestApplyParamsToCode:
    def test_module_constant(self) -> None:
        result = apply_params_to_code(_MODULE_CONST_CODE, {"BASE_SIZE": 20})
        assert "BASE_SIZE = 20" in result

    def test_pget(self) -> None:
        result = apply_params_to_code(_PGET_CODE, {"size": 25})
        assert 'p.get("size", 25)' in result

    def test_no_match_unchanged(self) -> None:
        result = apply_params_to_code(_MODULE_CONST_CODE, {"NONEXISTENT": 99})
        assert result == _MODULE_CONST_CODE
