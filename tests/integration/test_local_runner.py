"""Integration tests for the local runner."""

from __future__ import annotations

import json
from pathlib import Path

from data.schemas import TradingStateSchema
from trader.datamodel import TradingState
from trader.trader import Trader

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_states() -> list[TradingState]:
    raw = json.loads((FIXTURES_DIR / "sample_states.json").read_text())
    return [TradingStateSchema.model_validate(e).to_trading_state() for e in raw]


def _run_noop(states: list[TradingState]) -> list[dict[str, object]]:
    """Reproduce the run_local.run() logic inline for testing."""
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
    return results


class TestEndToEnd:
    def test_loads_and_runs(self) -> None:
        states = _load_states()
        assert len(states) == 5
        results = _run_noop(states)
        assert len(results) == 5
        for r in results:
            assert "timestamp" in r
            assert "orders" in r

    def test_determinism(self) -> None:
        states1 = _load_states()
        states2 = _load_states()
        r1 = _run_noop(states1)
        r2 = _run_noop(states2)
        assert json.dumps(r1) == json.dumps(r2)

    def test_trader_data_chains(self) -> None:
        """traderData output from tick N feeds into tick N+1."""
        states = _load_states()
        trader = Trader(strategy_name="noop")
        trader_data = "initial"
        for state in states:
            state.traderData = trader_data
            assert state.traderData == trader_data
            _, _, trader_data = trader.run(state)

    def test_empty_state_list(self) -> None:
        results = _run_noop([])
        assert results == []
