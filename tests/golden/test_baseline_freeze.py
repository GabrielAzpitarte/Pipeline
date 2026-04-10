"""Baseline freeze test — locks current engine behavior.

If any simulation change causes a baseline strategy's PnL to shift beyond
tolerance, this test fails. Investigate before updating the golden values.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.golden.baseline_package import BASELINE_STRATEGIES

DATA_PRICES = Path("data_raw/prices_round_0_day_-1.csv")
DATA_TRADES = Path("data_raw/trades_round_0_day_-1.csv")


@pytest.fixture(scope="module")
def backtest_data():
    """Load real backtest data (shared across all tests in this module)."""
    from data.parse_logs import load_round_data

    if not DATA_PRICES.exists() or not DATA_TRADES.exists():
        pytest.skip("Real backtest data not available")
    return load_round_data(DATA_PRICES, DATA_TRADES)


@pytest.mark.parametrize("name", list(BASELINE_STRATEGIES.keys()))
def test_baseline_pnl_frozen(name: str, backtest_data) -> None:
    """Verify each baseline strategy produces the expected PnL."""
    from experiments.sweep_runner import _sweep_worker

    info = BASELINE_STRATEGIES[name]
    source_path = Path(str(info["source"]))
    expected_pnl = float(str(info["known_backtest_pnl"]))
    tolerance = float(str(info.get("pnl_tolerance", 10)))

    if not source_path.exists():
        pytest.skip(f"Strategy file not found: {source_path}")

    source = source_path.read_text()
    _, _, metrics = _sweep_worker(
        (0, {}, source, backtest_data, False, 1.0, "all", "none", "one_sided", 0)
    )
    actual_pnl = metrics["total_pnl"]

    assert abs(actual_pnl - expected_pnl) <= tolerance, (
        f"{name}: PnL shifted from {expected_pnl} to {actual_pnl} "
        f"(delta={actual_pnl - expected_pnl:.0f}, tolerance={tolerance}). "
        f"Investigate before updating golden values."
    )
