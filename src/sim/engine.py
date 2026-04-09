"""Core simulation loop — the 'truth engine' for backtesting."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from data.parse_logs import BacktestData
from sim.limits import enforce_limits
from sim.matching import Fill, MarketTrade, TradeMatchingMode, match_orders
from sim.pnl import PnLTracker
from trader.datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    Trade,
    TradingState,
)
from trader.logging_utils import get_logger
from trader.risk import RiskLimits
from trader.trader import Trader

_log = get_logger("sim.engine")


@dataclass
class SimConfig:
    """Configuration knobs for the simulation."""

    trade_match_mode: TradeMatchingMode = TradeMatchingMode.ALL
    queue_penetration: float = 1.0  # jmerle default — full market trade volume available
    strategy_name: str = "noop"
    risk_limits: RiskLimits = field(default_factory=lambda: RiskLimits(max_order_size=9999))
    strategy_params: dict[str, Any] = field(default_factory=dict)
    data_split: float = 1.0
    execution_mode: str = "baseline"  # "baseline" = current behavior
    passive_fill_rate: float = 1.0  # 1.0 = fill all passive orders, <1.0 = stricter


@dataclass
class TickResult:
    """Results from a single simulation tick."""

    timestamp: int
    orders_submitted: dict[str, list[Order]]
    orders_after_limits: dict[str, list[Order]]
    fills: dict[str, list[Fill]]
    positions: dict[str, int]
    cash: float
    pnl: float
    mid_prices: dict[str, float]


@dataclass
class SimResult:
    """Complete simulation results."""

    ticks: list[TickResult] = field(default_factory=list)
    final_pnl: float = 0.0
    final_positions: dict[str, int] = field(default_factory=dict)
    final_cash: float = 0.0
    all_fills: list[Fill] = field(default_factory=list)


def _build_order_depth(
    bid_prices: list[int],
    bid_volumes: list[int],
    ask_prices: list[int],
    ask_volumes: list[int],
) -> OrderDepth:
    """Build an OrderDepth from price/volume lists."""
    od = OrderDepth()
    for p, v in zip(bid_prices, bid_volumes, strict=True):
        if v > 0:
            od.buy_orders[p] = v
    for p, v in zip(ask_prices, ask_volumes, strict=True):
        if v > 0:
            od.sell_orders[p] = -v  # negative per Prosperity convention
    return od


class SimEngine:
    """Run a strategy against historical data and collect results."""

    def __init__(self, config: SimConfig | None = None) -> None:
        self.config = config or SimConfig()

    def run(self, data: BacktestData) -> SimResult:
        """Execute simulation over the provided backtest data."""
        trader = Trader(
            strategy_name=self.config.strategy_name,
            params=self.config.strategy_params or None,
        )
        pnl_tracker = PnLTracker()
        result = SimResult()

        positions: dict[str, int] = {}
        own_trades: dict[str, list[Trade]] = {}
        trader_data: str = ""
        mid_prices: dict[str, float] = {}

        # Apply data split if configured
        timestamps = data.timestamps
        if self.config.data_split < 1.0:
            n = max(1, int(len(timestamps) * self.config.data_split))
            timestamps = timestamps[:n]

        _log.info("Starting sim: %d ticks, strategy=%s", len(timestamps), self.config.strategy_name)

        for timestamp in timestamps:
            # 1. Build order depths and listings from price data
            order_depths: dict[str, OrderDepth] = {}
            mid_prices = {}
            listings: dict[str, Listing] = {}

            for product, price_row in data.prices.get(timestamp, {}).items():
                order_depths[product] = _build_order_depth(
                    price_row.bid_prices,
                    price_row.bid_volumes,
                    price_row.ask_prices,
                    price_row.ask_volumes,
                )
                mid_prices[product] = price_row.mid_price
                listings[product] = Listing(product, product, "SEASHELLS")

            # 2. Build market trades for this tick
            raw_trades: dict[str, list[Trade]] = {}
            market_trades_mt: dict[str, list[MarketTrade]] = {}
            for product, trade_rows in data.trades.get(timestamp, {}).items():
                trades_list: list[Trade] = []
                mt_list: list[MarketTrade] = []
                for tr in trade_rows:
                    t = Trade(
                        symbol=tr.symbol,
                        price=tr.price,
                        quantity=tr.quantity,
                        buyer=tr.buyer,
                        seller=tr.seller,
                        timestamp=tr.timestamp,
                    )
                    trades_list.append(t)
                    # Apply queue penetration: scale available volume
                    qp = self.config.queue_penetration
                    bq = (
                        max(1, round(tr.quantity * qp))
                        if qp < 1.0 and tr.quantity > 0
                        else tr.quantity
                    )
                    sq = (
                        max(1, round(tr.quantity * qp))
                        if qp < 1.0 and tr.quantity > 0
                        else tr.quantity
                    )
                    mt_list.append(MarketTrade(trade=t, buy_quantity=bq, sell_quantity=sq))
                raw_trades[product] = trades_list
                market_trades_mt[product] = mt_list

            # 3. Build TradingState
            state = TradingState(
                timestamp=timestamp,
                traderData=trader_data,
                listings=listings,
                order_depths=copy.deepcopy(order_depths),
                own_trades=own_trades,
                market_trades={
                    s: [
                        Trade(t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp)
                        for t in tl
                    ]
                    for s, tl in raw_trades.items()
                },
                position=dict(positions),
                observations=Observation(),
            )

            # 4. Call trader (includes internal risk filtering)
            raw_orders, _conversions, trader_data = trader.run(
                state, risk_limits=self.config.risk_limits
            )

            # 5. Enforce Prosperity-faithful all-or-nothing position limits
            valid_orders = enforce_limits(raw_orders, positions)

            # 6. Match orders (jmerle/prosperity4bt semantics — no queue modeling)
            fills = match_orders(
                valid_orders,
                order_depths,
                market_trades_mt,
                self.config.trade_match_mode,
                passive_fill_rate=self.config.passive_fill_rate,
            )

            # 7. Process fills — update PnL tracker and positions
            tick_own_trades: dict[str, list[Trade]] = {}
            for symbol, fill_list in fills.items():
                tick_own_trades[symbol] = []
                for fill in fill_list:
                    pnl_tracker.record_fill(symbol, fill.price, fill.quantity)
                    positions[symbol] = positions.get(symbol, 0) + fill.quantity
                    result.all_fills.append(fill)
                    tick_own_trades[symbol].append(
                        Trade(
                            symbol=symbol,
                            price=fill.price,
                            quantity=abs(fill.quantity),
                            buyer="SUBMISSION" if fill.quantity > 0 else "",
                            seller="SUBMISSION" if fill.quantity < 0 else "",
                            timestamp=timestamp,
                        )
                    )

            own_trades = tick_own_trades

            # 8. Record tick result
            tick_pnl = pnl_tracker.total_pnl(mid_prices)
            result.ticks.append(
                TickResult(
                    timestamp=timestamp,
                    orders_submitted=raw_orders,
                    orders_after_limits=valid_orders,
                    fills=fills,
                    positions=dict(positions),
                    cash=pnl_tracker.cash,
                    pnl=tick_pnl,
                    mid_prices=dict(mid_prices),
                )
            )

        result.final_pnl = pnl_tracker.total_pnl(mid_prices)
        result.final_positions = dict(positions)
        result.final_cash = pnl_tracker.cash

        _log.info(
            "Sim complete: %d fills, final PnL=%.2f",
            len(result.all_fills),
            result.final_pnl,
        )

        return result
