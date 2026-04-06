#!/usr/bin/env python3
"""Local runner: replay recorded state sequences through a trader.

Usage:
    python scripts/run_local.py --data tests/fixtures/sample_states.json
    python scripts/run_local.py --data states.json --strategy noop --output results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure src/ is on the import path when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data.schemas import TradingStateSchema
from trader.datamodel import TradingState
from trader.trader import Trader


def load_states(path: Path) -> list[TradingState]:
    """Load a JSON file containing a list of TradingState snapshots."""
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON array, got {type(raw).__name__}")
    states: list[TradingState] = []
    for entry in raw:
        schema = TradingStateSchema.model_validate(entry)
        states.append(schema.to_trading_state())
    return states


def run(
    states: list[TradingState],
    strategy_name: str,
) -> list[dict[str, object]]:
    """Run trader over states, collecting results.

    Chains traderData from each tick's output into the next tick's input.
    """
    trader = Trader(strategy_name=strategy_name)
    results: list[dict[str, object]] = []
    trader_data = ""

    for state in states:
        # Inject traderData from previous tick.
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


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Replay states through a trader.")
    parser.add_argument("--data", type=Path, required=True, help="JSON file with state array")
    parser.add_argument(
        "--strategy", type=str, default="noop", help="Strategy name (default: noop)"
    )
    parser.add_argument("--output", type=Path, default=None, help="Write results to file")
    args = parser.parse_args()

    if not args.data.exists():
        print(f"Error: {args.data} not found", file=sys.stderr)
        sys.exit(1)

    states = load_states(args.data)
    results = run(states, args.strategy)

    output_text = json.dumps(results, indent=2)

    if args.output:
        args.output.write_text(output_text)
        print(f"Results written to {args.output}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
