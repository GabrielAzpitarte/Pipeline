"""Tests for submission/checklist.py."""

from __future__ import annotations

from pathlib import Path

from submission.checklist import validate_for_platform


class TestValidateForPlatform:
    def test_valid_strategy_passes(self, tmp_path: Path) -> None:
        code = """import math
class Trader:
    def run(self, state):
        return {}, 0, ""
"""
        p = tmp_path / "strategy.py"
        p.write_text(code)
        issues = validate_for_platform(p)
        assert len(issues) == 0

    def test_catches_internal_imports(self, tmp_path: Path) -> None:
        code = """from trader.utils import best_bid
class Trader:
    def run(self, state):
        return {}, 0, ""
"""
        p = tmp_path / "strategy.py"
        p.write_text(code)
        issues = validate_for_platform(p)
        assert any("Internal imports" in i for i in issues)

    def test_catches_missing_any_import(self, tmp_path: Path) -> None:
        code = """class Trader:
    def __init__(self, params: dict[str, Any] | None = None):
        pass
    def run(self, state):
        return {}, 0, ""
"""
        p = tmp_path / "strategy.py"
        p.write_text(code)
        issues = validate_for_platform(p)
        assert any("Any" in i for i in issues)

    def test_catches_missing_trader_class(self, tmp_path: Path) -> None:
        code = """class MyStrategy:
    def run(self, state):
        return {}, 0, ""
"""
        p = tmp_path / "strategy.py"
        p.write_text(code)
        issues = validate_for_platform(p)
        assert any("class Trader" in i for i in issues)

    def test_catches_syntax_error(self, tmp_path: Path) -> None:
        code = "def broken(:\n"
        p = tmp_path / "strategy.py"
        p.write_text(code)
        issues = validate_for_platform(p)
        assert any("Syntax error" in i for i in issues)

    def test_catches_numpy(self, tmp_path: Path) -> None:
        code = """import numpy as np
class Trader:
    def run(self, state):
        return {}, 0, ""
"""
        p = tmp_path / "strategy.py"
        p.write_text(code)
        issues = validate_for_platform(p)
        assert any("numpy" in i for i in issues)
