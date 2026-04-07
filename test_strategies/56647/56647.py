"""Hybrid optimal asset specialist — per-asset logic, Gemini R3."""
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

ORDER_SIZE = 15
EMERALD_EDGE = 2
TOMATO_BASE_EDGE = 3
EMA_ALPHA = 0.15
MOMENTUM_WEIGHT = 0.3
INVENTORY_SKEW = 0.5
UNWIND_THRESHOLD = 55

class Trader:
    def __init__(self):
        self.ema_prices = {}
        self.last_prices = {}

    def run(self, state):
        orders = {}
        for symbol, depth in state.order_depths.items():
            if not depth.buy_orders or not depth.sell_orders: continue
            if symbol == "EMERALDS":
                orders[symbol] = self._emeralds(symbol, depth, state)
            elif symbol == "TOMATOES":
                orders[symbol] = self._tomatoes(symbol, depth, state)
        return orders, 0, ""

    def _emeralds(self, symbol, depth, state):
        fair = 10000; pos = state.position.get(symbol, 0)
        bb = max(depth.buy_orders.keys()); ba = min(depth.sell_orders.keys())
        if abs(pos) > UNWIND_THRESHOLD:
            if pos > 0: return [Order(symbol, bb, -min(20, pos))]
            else: return [Order(symbol, ba, min(20, -pos))]
        buy_price = min(bb + 1, fair - EMERALD_EDGE)
        sell_price = max(ba - 1, fair + EMERALD_EDGE)
        return [Order(symbol, buy_price, ORDER_SIZE), Order(symbol, sell_price, -ORDER_SIZE)]

    def _tomatoes(self, symbol, depth, state):
        pos = state.position.get(symbol, 0)
        bb = max(depth.buy_orders.keys()); ba = min(depth.sell_orders.keys())
        if abs(pos) > UNWIND_THRESHOLD:
            if pos > 0: return [Order(symbol, bb, -min(20, pos))]
            else: return [Order(symbol, ba, min(20, -pos))]
        # Microprice
        bv = sum(depth.buy_orders.values()); av = sum(-v for v in depth.sell_orders.values())
        microprice = (bb * av + ba * bv) / (av + bv) if av + bv > 0 else (bb+ba)/2
        # EMA fair value with momentum
        if symbol not in self.ema_prices:
            self.ema_prices[symbol] = microprice; self.last_prices[symbol] = microprice
        ema = EMA_ALPHA * microprice + (1 - EMA_ALPHA) * self.ema_prices[symbol]
        momentum = microprice - self.last_prices[symbol]
        self.ema_prices[symbol] = ema; self.last_prices[symbol] = microprice
        fair = ema + MOMENTUM_WEIGHT * momentum
        # Vol and edge
        vol = abs(microprice - ema)
        edge = int(TOMATO_BASE_EDGE * (1 + vol / 50))
        inv_adj = int(INVENTORY_SKEW * pos / 10)
        # OBI
        obi = (bv - av) / (bv + av) if bv + av > 0 else 0
        buy_price = int(fair) - edge - inv_adj if obi < -0.2 else bb + 1
        sell_price = int(fair) + edge - inv_adj if obi > 0.2 else ba - 1
        return [Order(symbol, buy_price, ORDER_SIZE), Order(symbol, sell_price, -ORDER_SIZE)]
