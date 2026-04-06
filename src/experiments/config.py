"""Load experiment configuration from TOML files."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sim.engine import SimConfig
from sim.matching import TradeMatchingMode
from trader.risk import RiskLimits

_TRADE_MATCH_MODES: dict[str, TradeMatchingMode] = {
    "all": TradeMatchingMode.ALL,
    "worse": TradeMatchingMode.WORSE,
    "none": TradeMatchingMode.NONE,
}


@dataclass
class ExperimentConfig:
    """Parsed experiment configuration from a TOML file."""

    name: str
    strategy: str
    dataset_description: str
    tags: list[str]
    prices_path: Path
    trades_path: Path
    sim_config: SimConfig
    strategy_params: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)


def load_config(path: Path) -> ExperimentConfig:
    """Load and validate an experiment config from a TOML file.

    Expected structure::

        [experiment]
        name = "..."
        strategy = "..."
        dataset_description = "..."   # optional
        tags = ["...", "..."]         # optional

        [data]
        prices = "path/to/prices.csv"
        trades = "path/to/trades.csv"

        [sim]                         # optional
        trade_match_mode = "all"

        [params]                      # optional — strategy parameters
        spread = 4

        [sweep]                       # optional — parameter grid for sweeps
        spread = [2, 3, 4]
    """
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    exp = raw.get("experiment", {})
    data_section = raw.get("data", {})
    sim_section = raw.get("sim", {})
    params = raw.get("params", {})

    name = exp.get("name", "")
    strategy = exp.get("strategy", "")
    if not name or not strategy:
        raise ValueError(f"Config {path} must have [experiment] name and strategy")

    if not data_section.get("prices") or not data_section.get("trades"):
        raise ValueError(f"Config {path} must have [data] prices and trades paths")

    prices_path = Path(data_section["prices"])
    trades_path = Path(data_section["trades"])

    mode_str = sim_section.get("trade_match_mode", "all").lower()
    mode = _TRADE_MATCH_MODES.get(mode_str)
    if mode is None:
        raise ValueError(f"Unknown trade_match_mode: {mode_str!r}")

    risk_limits = RiskLimits(
        max_order_size=sim_section.get("max_order_size", 9999),
        max_open_orders=sim_section.get("max_open_orders", 50),
    )

    sim_config = SimConfig(
        trade_match_mode=mode,
        strategy_name=strategy,
        strategy_params=params,
        risk_limits=risk_limits,
        data_split=sim_section.get("data_split", 1.0),
    )

    return ExperimentConfig(
        name=name,
        strategy=strategy,
        dataset_description=exp.get("dataset_description", ""),
        tags=exp.get("tags", []),
        prices_path=prices_path,
        trades_path=trades_path,
        sim_config=sim_config,
        strategy_params=params,
        raw=raw,
    )
