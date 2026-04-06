"""Tests for Prosperity CSV parsing."""

from __future__ import annotations

from pathlib import Path

from data.parse_logs import (
    BacktestData,
    PriceRow,
    TradeRow,
    load_round_data,
    parse_prices_csv,
    parse_trades_csv,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class TestParsePricesCsv:
    def test_parses_sample(self) -> None:
        rows = parse_prices_csv(FIXTURES_DIR / "sample_prices.csv")
        assert len(rows) == 6  # 3 timestamps x 2 products

    def test_row_fields(self) -> None:
        rows = parse_prices_csv(FIXTURES_DIR / "sample_prices.csv")
        first = rows[0]
        assert isinstance(first, PriceRow)
        assert first.day == 1
        assert first.timestamp == 100
        assert first.product == "RAINFOREST_RESIN"
        assert first.bid_prices[0] == 9998
        assert first.bid_volumes[0] == 10
        assert first.ask_prices[0] == 10002
        assert first.ask_volumes[0] == 10
        assert first.mid_price == 10000.0

    def test_missing_levels_filtered(self) -> None:
        """KELP only has 2 bid/ask levels in the sample."""
        rows = parse_prices_csv(FIXTURES_DIR / "sample_prices.csv")
        kelp_rows = [r for r in rows if r.product == "KELP"]
        assert len(kelp_rows) == 3
        assert len(kelp_rows[0].bid_prices) == 2  # only 2 levels with volume > 0


class TestParseTradesCsv:
    def test_parses_sample(self) -> None:
        rows = parse_trades_csv(FIXTURES_DIR / "sample_trades.csv")
        assert len(rows) == 6

    def test_row_fields(self) -> None:
        rows = parse_trades_csv(FIXTURES_DIR / "sample_trades.csv")
        first = rows[0]
        assert isinstance(first, TradeRow)
        assert first.buyer == "bot_a"
        assert first.seller == "bot_b"
        assert first.symbol == "RAINFOREST_RESIN"
        assert first.price == 10000
        assert first.quantity == 5


class TestLoadRoundData:
    def test_loads_and_groups(self) -> None:
        data = load_round_data(
            FIXTURES_DIR / "sample_prices.csv",
            FIXTURES_DIR / "sample_trades.csv",
        )
        assert isinstance(data, BacktestData)
        assert data.timestamps == [100, 200, 300]
        assert "RAINFOREST_RESIN" in data.products
        assert "KELP" in data.products

    def test_prices_grouped_by_timestamp(self) -> None:
        data = load_round_data(
            FIXTURES_DIR / "sample_prices.csv",
            FIXTURES_DIR / "sample_trades.csv",
        )
        assert "RAINFOREST_RESIN" in data.prices[100]
        assert "KELP" in data.prices[100]

    def test_trades_grouped_by_timestamp(self) -> None:
        data = load_round_data(
            FIXTURES_DIR / "sample_prices.csv",
            FIXTURES_DIR / "sample_trades.csv",
        )
        resin_trades = data.trades[100]["RAINFOREST_RESIN"]
        assert len(resin_trades) == 1
        assert resin_trades[0].price == 10000
