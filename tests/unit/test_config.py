"""Tests for experiments/config.py — TOML config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.config import load_config
from sim.matching import TradeMatchingMode


def _write_toml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "test.toml"
    p.write_text(content)
    return p


class TestLoadConfig:
    def test_minimal_config(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[experiment]
name = "test"
strategy = "noop"

[data]
prices = "tests/fixtures/sample_prices.csv"
trades = "tests/fixtures/sample_trades.csv"
""",
        )
        cfg = load_config(path)
        assert cfg.name == "test"
        assert cfg.strategy == "noop"
        assert cfg.sim_config.trade_match_mode == TradeMatchingMode.ALL

    def test_missing_name_raises(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[experiment]
strategy = "noop"

[data]
prices = "p.csv"
trades = "t.csv"
""",
        )
        with pytest.raises(ValueError, match="name"):
            load_config(path)

    def test_missing_data_raises(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[experiment]
name = "test"
strategy = "noop"
""",
        )
        with pytest.raises(ValueError, match="prices and trades"):
            load_config(path)

    def test_custom_trade_match_mode(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[experiment]
name = "test"
strategy = "noop"

[data]
prices = "p.csv"
trades = "t.csv"

[sim]
trade_match_mode = "none"
""",
        )
        cfg = load_config(path)
        assert cfg.sim_config.trade_match_mode == TradeMatchingMode.NONE

    def test_invalid_trade_match_mode_raises(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[experiment]
name = "test"
strategy = "noop"

[data]
prices = "p.csv"
trades = "t.csv"

[sim]
trade_match_mode = "invalid"
""",
        )
        with pytest.raises(ValueError, match="Unknown trade_match_mode"):
            load_config(path)

    def test_params_parsed(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[experiment]
name = "test"
strategy = "noop"

[data]
prices = "p.csv"
trades = "t.csv"

[params]
spread = 4
max_pos = 15
""",
        )
        cfg = load_config(path)
        assert cfg.strategy_params["spread"] == 4
        assert cfg.strategy_params["max_pos"] == 15

    def test_sweep_in_raw(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[experiment]
name = "test"
strategy = "noop"

[data]
prices = "p.csv"
trades = "t.csv"

[sweep]
spread = [2, 3, 4]
""",
        )
        cfg = load_config(path)
        assert cfg.raw["sweep"]["spread"] == [2, 3, 4]

    def test_tags_default_empty(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[experiment]
name = "test"
strategy = "noop"

[data]
prices = "p.csv"
trades = "t.csv"
""",
        )
        cfg = load_config(path)
        assert cfg.tags == []
