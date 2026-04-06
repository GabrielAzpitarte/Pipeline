"""Fast simulator for cheap strategy screening.

NOT faithful to the Prosperity matching engine. Designed to preserve
strategy RANKING, not exact PnL. Use SimEngine for accurate backtests.

Simplifications vs SimEngine:
  - No market trade matching (Phase 2 skipped)
  - No order book consumption (book is read-only)
  - Simplified fill: buy crosses best ask -> fill at best ask, qty capped
  - No deepcopy of order depths
  - Individual position checks instead of all-or-nothing
"""

from __future__ import annotations

from data.parse_logs import BacktestData
from sim.engine import SimConfig, SimResult, TickResult, _build_order_depth
from sim.limits import get_limit
from sim.matching import Fill
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
from trader.trader import Trader

_log = get_logger("sim.fast_engine")


def _fast_match_order(order: Order, depth: OrderDepth) -> Fill | None:
    """Simplified matching: cross best level only, no book mutation.

    Returns a single Fill or None if the order doesn't cross the spread.
    """
    if order.quantity > 0:
        if not depth.sell_orders:
            return None
        best_ask = min(depth.sell_orders.keys())
        if order.price < best_ask:
            return None
        available = abs(depth.sell_orders[best_ask])
        fill_qty = min(order.quantity, available)
        return Fill(symbol=order.symbol, price=best_ask, quantity=fill_qty, against="book")
    elif order.quantity < 0:
        if not depth.buy_orders:
            return None
        best_bid = max(depth.buy_orders.keys())
        if order.price > best_bid:
            return None
        available = depth.buy_orders[best_bid]
        fill_qty = min(abs(order.quantity), available)
        return Fill(symbol=order.symbol, price=best_bid, quantity=-fill_qty, against="book")
    return None


def _fast_match_all(
    orders: dict[str, list[Order]],
    depths: dict[str, OrderDepth],
) -> dict[str, list[Fill]]:
    """Match all orders using simplified fast matching."""
    all_fills: dict[str, list[Fill]] = {}
    for symbol, order_list in orders.items():
        depth = depths.get(symbol)
        if depth is None:
            continue
        symbol_fills: list[Fill] = []
        for order in order_list:
            fill = _fast_match_order(order, depth)
            if fill is not None:
                symbol_fills.append(fill)
        if symbol_fills:
            all_fills[symbol] = symbol_fills
    return all_fills


def _simple_position_check(
    orders: dict[str, list[Order]],
    positions: dict[str, int],
) -> dict[str, list[Order]]:
    """Simplified position enforcement: reject individual orders that breach limits."""
    accepted: dict[str, list[Order]] = {}
    for symbol, order_list in orders.items():
        limit = get_limit(symbol)
        pos = positions.get(symbol, 0)
        sym_accepted: list[Order] = []
        for order in order_list:
            new_pos = pos + order.quantity
            if abs(new_pos) <= limit:
                sym_accepted.append(order)
                pos = new_pos
        if sym_accepted:
            accepted[symbol] = sym_accepted
    return accepted


class FastSimEngine:
    """Fast simulator for strategy screening. Same interface as SimEngine."""

    def __init__(self, config: SimConfig | None = None) -> None:
        self.config = config or SimConfig()

    def run(self, data: BacktestData) -> SimResult:
        """Execute fast simulation over the provided backtest data."""
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

        _log.info(
            "Fast sim: %d ticks, strategy=%s",
            len(data.timestamps),
            self.config.strategy_name,
        )

        for timestamp in data.timestamps:
            # 1. Build order depths (NO deepcopy)
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

            # 2. Build TradingState (no market trades for fast sim)
            state = TradingState(
                timestamp=timestamp,
                traderData=trader_data,
                listings=listings,
                order_depths=order_depths,
                own_trades=own_trades,
                market_trades={},
                position=dict(positions),
                observations=Observation(),
            )

            # 3. Get orders from trader
            raw_orders, _conversions, trader_data = trader.run(
                state, risk_limits=self.config.risk_limits
            )

            # 4. Simple position check
            valid_orders = _simple_position_check(raw_orders, positions)

            # 5. Fast matching
            fills = _fast_match_all(valid_orders, order_depths)

            # 6. Process fills
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

            # 7. Record tick
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
            "Fast sim complete: %d fills, final PnL=%.2f",
            len(result.all_fills),
            result.final_pnl,
        )

        return result
