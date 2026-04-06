"""Parse Prosperity competition CSV files into structured data."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PriceRow:
    """One row from a Prosperity prices CSV."""

    day: int
    timestamp: int
    product: str
    bid_prices: list[int]
    bid_volumes: list[int]
    ask_prices: list[int]
    ask_volumes: list[int]
    mid_price: float
    profit_loss: float


@dataclass
class TradeRow:
    """One row from a Prosperity trades CSV."""

    day: int
    timestamp: int
    buyer: str
    seller: str
    symbol: str
    currency: str
    price: int
    quantity: int


@dataclass
class BacktestData:
    """All data needed for a backtest run."""

    timestamps: list[int]
    prices: dict[int, dict[str, PriceRow]] = field(default_factory=dict)
    trades: dict[int, dict[str, list[TradeRow]]] = field(default_factory=dict)
    products: set[str] = field(default_factory=set)


def _parse_int_or_zero(val: str) -> int:
    """Parse an int, returning 0 for empty/invalid strings."""
    val = val.strip()
    if not val:
        return 0
    return int(float(val))


def _parse_float_or_zero(val: str) -> float:
    """Parse a float, returning 0.0 for empty/invalid strings."""
    val = val.strip()
    if not val:
        return 0.0
    return float(val)


def parse_prices_csv(path: Path) -> list[PriceRow]:
    """Parse a Prosperity prices CSV (semicolon-delimited).

    Expected header:
        day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;
        bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;
        ask_price_3;ask_volume_3;mid_price;profit_and_loss
    """
    rows: list[PriceRow] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for raw in reader:
            bid_prices: list[int] = []
            bid_volumes: list[int] = []
            ask_prices: list[int] = []
            ask_volumes: list[int] = []

            for i in range(1, 4):
                bp = _parse_int_or_zero(raw.get(f"bid_price_{i}", ""))
                bv = _parse_int_or_zero(raw.get(f"bid_volume_{i}", ""))
                if bv > 0:
                    bid_prices.append(bp)
                    bid_volumes.append(bv)

                ap = _parse_int_or_zero(raw.get(f"ask_price_{i}", ""))
                av = _parse_int_or_zero(raw.get(f"ask_volume_{i}", ""))
                if av > 0:
                    ask_prices.append(ap)
                    ask_volumes.append(av)

            rows.append(
                PriceRow(
                    day=_parse_int_or_zero(raw.get("day", "0")),
                    timestamp=_parse_int_or_zero(raw.get("timestamp", "0")),
                    product=raw.get("product", "").strip(),
                    bid_prices=bid_prices,
                    bid_volumes=bid_volumes,
                    ask_prices=ask_prices,
                    ask_volumes=ask_volumes,
                    mid_price=_parse_float_or_zero(raw.get("mid_price", "0")),
                    profit_loss=_parse_float_or_zero(raw.get("profit_and_loss", "0")),
                )
            )
    return rows


def parse_trades_csv(path: Path) -> list[TradeRow]:
    """Parse a Prosperity trades CSV (semicolon-delimited).

    Expected header:
        timestamp;buyer;seller;symbol;currency;price;quantity
    """
    rows: list[TradeRow] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for raw in reader:
            rows.append(
                TradeRow(
                    day=_parse_int_or_zero(raw.get("day", "0")),
                    timestamp=_parse_int_or_zero(raw.get("timestamp", "0")),
                    buyer=raw.get("buyer", "").strip(),
                    seller=raw.get("seller", "").strip(),
                    symbol=raw.get("symbol", "").strip(),
                    currency=raw.get("currency", "").strip(),
                    price=_parse_int_or_zero(raw.get("price", "0")),
                    quantity=_parse_int_or_zero(raw.get("quantity", "0")),
                )
            )
    return rows


def load_round_data(prices_path: Path, trades_path: Path) -> BacktestData:
    """Load prices and trades CSVs into a BacktestData for the sim engine."""
    price_rows = parse_prices_csv(prices_path)
    trade_rows = parse_trades_csv(trades_path)

    prices: dict[int, dict[str, PriceRow]] = defaultdict(dict)
    products: set[str] = set()
    timestamp_set: set[int] = set()

    for row in price_rows:
        prices[row.timestamp][row.product] = row
        products.add(row.product)
        timestamp_set.add(row.timestamp)

    trades: dict[int, dict[str, list[TradeRow]]] = defaultdict(lambda: defaultdict(list))
    for trade_row in trade_rows:
        trades[trade_row.timestamp][trade_row.symbol].append(trade_row)
        timestamp_set.add(trade_row.timestamp)

    return BacktestData(
        timestamps=sorted(timestamp_set),
        prices=dict(prices),
        trades={ts: dict(prods) for ts, prods in trades.items()},
        products=products,
    )
