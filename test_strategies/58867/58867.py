"""Liquidity momentum sniper — OpenAI R1, backtest 15003."""
import math
from typing import Dict, List
Time=int;Symbol=str;Product=str;Position=int;UserId=str;ObservationValue=int
class Listing:
    def __init__(s,symbol,product,denomination):s.symbol=symbol;s.product=product;s.denomination=denomination
class ConversionObservation:
    def __init__(s,bidPrice,askPrice,transportFees,exportTariff,importTariff,sugarPrice,sunlightIndex):s.bidPrice=bidPrice;s.askPrice=askPrice;s.transportFees=transportFees;s.exportTariff=exportTariff;s.importTariff=importTariff;s.sugarPrice=sugarPrice;s.sunlightIndex=sunlightIndex
class Observation:
    def __init__(s,plainValueObservations=None,conversionObservations=None):s.plainValueObservations=plainValueObservations or{};s.conversionObservations=conversionObservations or{}
class Order:
    def __init__(s,symbol,price,quantity):s.symbol=symbol;s.price=price;s.quantity=quantity
class OrderDepth:
    def __init__(s):s.buy_orders={};s.sell_orders={}
class Trade:
    def __init__(s,symbol,price,quantity,buyer="",seller="",timestamp=0):s.symbol=symbol;s.price=price;s.quantity=quantity;s.buyer=buyer;s.seller=seller;s.timestamp=timestamp
class TradingState:
    def __init__(s,timestamp,traderData,listings,order_depths,own_trades,market_trades,position,observations):s.timestamp=timestamp;s.traderData=traderData;s.listings=listings;s.order_depths=order_depths;s.own_trades=own_trades;s.market_trades=market_trades;s.position=position;s.observations=observations

class Trader:
    """Combines passive market-making with aggressive sniping on dislocations."""

    def __init__(self, params: dict  = None) -> None:
        p = params or {}
        self.base_size: int = int(p.get("base_size", 15))
        self.ema_alpha: float = float(p.get("ema_alpha", 0.15))
        self.momentum_weight: float = float(p.get("momentum_weight", 0.3))
        self.volatility_window: int = int(p.get("volatility_window", 10))
        self.edge_multiplier: float = float(p.get("edge_multiplier", 1.5))
        self.imbalance_threshold: float = float(p.get("imbalance_threshold", 0.7))
        self.inventory_skew: float = float(p.get("inventory_skew", 0.2))
        self.unwind_threshold: int = int(p.get("unwind_threshold", 50))
        self.prices: dict[str, list[float]] = {}
        self.ema: dict[str, float] = {}

    def compute_orders(self, state):
        """Generate orders based on symbol-specific logic."""
        orders: dict[str, list[Order]] = {}
        for symbol, depth in state.order_depths.items():
            if symbol == "EMERALDS":
                orders[symbol] = self._emeralds_orders(state, symbol, depth)
            elif symbol == "TOMATOES":
                orders[symbol] = self._tomatoes_orders(state, symbol, depth)
        return orders

    def _emeralds_orders(self, state: TradingState, symbol: str, depth) -> list[Order]:
        """Static fair value market-making for EMERALDS."""
        fair_value = 10000
        pos = state.position.get(symbol, 0)
        bid = best_bid(depth)
        ask = best_ask(depth)
        if bid is None or ask is None:
            return []

        size = max(5, self.base_size - abs(pos) // 5)
        skew = int(pos * self.inventory_skew)

        orders = []
        if abs(pos) > self.unwind_threshold:
            unwind_price = fair_value - skew
            orders.append(Order(symbol, unwind_price, -pos // 2 if pos > 0 else -pos // 2))
        else:
            buy_price = min(bid + 1, fair_value - 1 - skew)
            sell_price = max(ask - 1, fair_value + 1 - skew)
            orders.extend([
                Order(symbol, buy_price, size),
                Order(symbol, sell_price, -size)
            ])
        return orders

    def _tomatoes_orders(self, state: TradingState, symbol: str, depth) -> list[Order]:
        """Dynamic fair value with momentum and sniping for TOMATOES."""
        bid = best_bid(depth)
        ask = best_ask(depth)
        if bid is None or ask is None:
            return []

        # Compute microprice
        bid_size = sum(depth.buy_orders.values())
        ask_size = sum(-v for v in depth.sell_orders.values())
        if bid_size + ask_size > 0:
            microprice = (bid * ask_size + ask * bid_size) / (bid_size + ask_size)
        else:
            microprice = (bid + ask) / 2

        # Update EMA
        if symbol not in self.ema:
            self.ema[symbol] = microprice
        else:
            self.ema[symbol] = self.ema_alpha * microprice + (1 - self.ema_alpha) * self.ema[symbol]

        # Track prices for volatility
        if symbol not in self.prices:
            self.prices[symbol] = []
        self.prices[symbol].append(microprice)
        if len(self.prices[symbol]) > self.volatility_window:
            self.prices[symbol].pop(0)

        # Compute momentum and volatility
        momentum = microprice - self.ema[symbol] if len(self.prices[symbol]) > 1 else 0
        volatility = math.sqrt(sum((p - self.ema[symbol])**2 for p in self.prices[symbol]) / len(self.prices[symbol])) if len(self.prices[symbol]) > 1 else 1

        # Dynamic fair value
        fair_value = self.ema[symbol] + momentum * self.momentum_weight
        edge = max(2, int(volatility * self.edge_multiplier))

        pos = state.position.get(symbol, 0)
        size = max(5, self.base_size - abs(pos) // 5)
        skew = int(pos * self.inventory_skew)

        orders = []

        # Check for unwind
        if abs(pos) > self.unwind_threshold:
            unwind_price = int(fair_value - skew)
            orders.append(Order(symbol, unwind_price, -pos // 2 if pos > 0 else -pos // 2))
            return orders

        # Check imbalance for sniping
        imbalance = (bid_size - ask_size) / (bid_size + ask_size) if bid_size + ask_size > 0 else 0

        if ask < fair_value - edge or imbalance > self.imbalance_threshold:
            orders.append(Order(symbol, ask, size))
        elif bid > fair_value + edge or imbalance < -self.imbalance_threshold:
            orders.append(Order(symbol, bid, -size))
        else:
            # Normal market making
            buy_price = min(bid + 1, int(fair_value - 1 - skew))
            sell_price = max(ask - 1, int(fair_value + 1 - skew))
            orders.extend([
                Order(symbol, buy_price, size),
                Order(symbol, sell_price, -size)
            ])

        return orders

    def run(self, state):
        return self.compute_orders(state), 0, ""
