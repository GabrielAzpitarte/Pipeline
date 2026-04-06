"""Shared test fixtures and helpers."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless backend for CI/testing

from experiments.models import RunData, RunMetadata, StoredFill


def make_test_run_data(
    n_ticks: int = 5,
    products: list[str] | None = None,
    n_fills: int = 2,
    strategy: str = "test_strat",
) -> RunData:
    """Create a synthetic RunData for testing."""
    prods = products or ["AMETHYSTS"]
    base_price = 10000
    timestamps = list(range(100, 100 + n_ticks * 100, 100))

    pnl_series: list[float] = []
    position_series: list[dict[str, int]] = []
    cash_series: list[float] = []
    mid_price_series: list[dict[str, float]] = []
    orders_submitted: list[dict[str, list[dict[str, int]]]] = []
    fills: list[StoredFill] = []

    cash = 0.0
    positions: dict[str, int] = {p: 0 for p in prods}

    for i, ts in enumerate(timestamps):
        # Generate fills for the first n_fills ticks
        if i < n_fills:
            for p in prods:
                qty = 5 if i % 2 == 0 else -5
                price = base_price + i
                fills.append(
                    StoredFill(timestamp=ts, symbol=p, price=price, quantity=qty, against="book")
                )
                cash -= price * qty
                positions[p] += qty

        mid_prices = {p: float(base_price + i) for p in prods}
        unrealized = sum(positions[p] * mid_prices[p] for p in prods)
        pnl_series.append(cash + unrealized)
        position_series.append(dict(positions))
        cash_series.append(cash)
        mid_price_series.append(mid_prices)
        orders_submitted.append({p: [{"price": base_price, "quantity": 5}] for p in prods})

    return RunData(
        metadata=RunMetadata(
            run_id=f"test_run_{strategy}",
            timestamp="2026-04-01T12:00:00+00:00",
            strategy_name=strategy,
            config={"strategy_name": strategy, "trade_match_mode": "all"},
            git_hash="abc123",
            dataset_description="test data",
            tags=["test"],
        ),
        timestamps=timestamps,
        pnl_series=pnl_series,
        position_series=position_series,
        cash_series=cash_series,
        mid_price_series=mid_price_series,
        fills=fills,
        orders_submitted=orders_submitted,
        final_pnl=pnl_series[-1],
        final_positions=dict(positions),
        final_cash=cash,
    )
