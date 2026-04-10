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
    trade_split: str = "one_sided"  # "one_sided" | "half" (legacy) | "probabilistic"


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


def run_simulation(
    trader_callable: Any,
    data: BacktestData,
    trade_match_mode: TradeMatchingMode = TradeMatchingMode.ALL,
    passive_fill_rate: float = 1.0,
    queue_penetration: float = 1.0,
    queue_model: str = "none",
    trade_split: str = "one_sided",
    latency_ticks: int = 0,
    data_split: float = 1.0,
    risk_limits: RiskLimits | None = None,
) -> SimResult:
    """Core simulation loop — single source of execution truth.

    This is the ONE authoritative simulation path. Both SimEngine and
    sweep workers must call this function.

    Args:
        trader_callable: A trader instance with ``run(state)`` method.
            Can be a registry Trader or a standalone Trader from exec().
        data: Parsed backtest data.
        trade_match_mode: How to match against market trades.
        passive_fill_rate: Fraction of same-price passive fills granted.
        queue_penetration: Scaling factor for trade liquidity.
        data_split: Fraction of data to use (1.0 = all).
        risk_limits: Optional risk limits for registry-style Trader.
    """
    pnl_tracker = PnLTracker()
    result = SimResult()

    positions: dict[str, int] = {}
    own_trades: dict[str, list[Trade]] = {}
    trader_data: str = ""
    mid_prices: dict[str, float] = {}

    timestamps = data.timestamps
    if data_split < 1.0:
        n = max(1, int(len(timestamps) * data_split))
        timestamps = timestamps[:n]

    _log.info("Starting sim: %d ticks", len(timestamps))

    # Pending orders for latency simulation
    pending_orders: dict[int, dict[str, list[Any]]] = {}  # tick_index → orders

    for tick_idx, timestamp in enumerate(timestamps):
        # 1. Build order depths and listings
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

        # 2. Build market trades (split liquidity between sides)
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
                # Build MarketTrade with trade_split policy
                if trade_split == "one_sided":
                    # Deterministic one-sided: trade goes to one side only
                    side = (tr.timestamp * 31 + tr.price * 17) % 2
                    bq = tr.quantity if side == 0 else 0
                    sq = tr.quantity if side == 1 else 0
                elif trade_split == "probabilistic":
                    # Random one-sided with reproducible seed per trade
                    import random as _random

                    _rng = _random.Random(tr.timestamp * 1000 + tr.price)
                    if _rng.random() > 0.5:
                        bq, sq = tr.quantity, 0
                    else:
                        bq, sq = 0, tr.quantity
                elif trade_split == "half":
                    # Legacy: split between sides (creates artificial symmetric liquidity)
                    bq = max(1, tr.quantity // 2)
                    sq = bq
                else:
                    # Unknown mode — fall back to one_sided
                    side = (tr.timestamp * 31 + tr.price * 17) % 2
                    bq = tr.quantity if side == 0 else 0
                    sq = tr.quantity if side == 1 else 0
                if queue_penetration < 1.0:
                    bq = max(0, round(bq * queue_penetration)) if bq > 0 else 0
                    sq = max(0, round(sq * queue_penetration)) if sq > 0 else 0
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
                    Trade(t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp) for t in tl
                ]
                for s, tl in raw_trades.items()
            },
            position=dict(positions),
            observations=Observation(),
        )

        # 4. Call trader
        if risk_limits is not None and hasattr(trader_callable, "run"):
            # Registry-style Trader with risk filtering
            try:
                raw_orders, _conversions, trader_data = trader_callable.run(
                    state, risk_limits=risk_limits
                )
            except TypeError:
                # Standalone Trader without risk_limits param
                run_result = trader_callable.run(state)
                if isinstance(run_result, tuple):
                    raw_orders = run_result[0]
                    trader_data = run_result[2] if len(run_result) > 2 else ""
                else:
                    raw_orders = run_result
                    trader_data = ""
        else:
            run_result = trader_callable.run(state)
            if isinstance(run_result, tuple):
                raw_orders = run_result[0]
                trader_data = run_result[2] if len(run_result) > 2 else ""
            else:
                raw_orders = run_result
                trader_data = ""

        # 5. Apply latency: delay orders if latency_ticks > 0
        if latency_ticks > 0:
            # Store current orders for future tick
            future_idx = tick_idx + latency_ticks
            pending_orders[future_idx] = raw_orders
            # Use matured orders from earlier ticks (if any)
            raw_orders = pending_orders.pop(tick_idx, {})

        # 6. Enforce position limits
        valid_orders = enforce_limits(raw_orders, positions)

        # 6. Build queue maps if queue model is active
        buy_queues = None
        sell_queues = None
        if queue_model == "simple":
            buy_queues = {sym: dict(depth.buy_orders) for sym, depth in order_depths.items()}
            sell_queues = {
                sym: {p: abs(v) for p, v in depth.sell_orders.items()}
                for sym, depth in order_depths.items()
            }

        # 7. Match orders
        fills = match_orders(
            valid_orders,
            order_depths,
            market_trades_mt,
            trade_match_mode,
            buy_queues=buy_queues,
            sell_queues=sell_queues,
            passive_fill_rate=passive_fill_rate,
        )

        # 7. Process fills
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

        return run_simulation(
            trader_callable=trader,
            data=data,
            trade_match_mode=self.config.trade_match_mode,
            passive_fill_rate=self.config.passive_fill_rate,
            queue_penetration=self.config.queue_penetration,
            trade_split=self.config.trade_split,
            data_split=self.config.data_split,
            risk_limits=self.config.risk_limits,
        )
