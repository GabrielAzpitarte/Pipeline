"""Golden test: noop strategy output must match the locked expected output."""

from __future__ import annotations

import json
from pathlib import Path

from data.schemas import TradingStateSchema
from trader.datamodel import TradingState
from trader.trader import Trader

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_noop_golden_output() -> None:
    """Run noop on sample_states and compare to expected_noop_output.json."""
    raw = json.loads((FIXTURES_DIR / "sample_states.json").read_text())
    expected = json.loads((FIXTURES_DIR / "expected_noop_output.json").read_text())

    states: list[TradingState] = [
        TradingStateSchema.model_validate(e).to_trading_state() for e in raw
    ]

    trader = Trader(strategy_name="noop")
    results: list[dict[str, object]] = []
    trader_data = ""

    for state in states:
        state.traderData = trader_data
        orders, conversions, trader_data = trader.run(state)
        results.append(
            {
                "timestamp": state.timestamp,
                "orders": {
                    sym: [{"price": o.price, "quantity": o.quantity} for o in ords]
                    for sym, ords in orders.items()
                },
                "conversions": conversions,
                "traderData": trader_data,
            }
        )

    assert results == expected, (
        f"Golden output mismatch.\nGot: {json.dumps(results, indent=2)}\n"
        f"Expected: {json.dumps(expected, indent=2)}"
    )
