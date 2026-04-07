"""Assembled best per-asset: taker_penny EMERALDS + microprice TOMATOES."""
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
    def __init__(self):
        # TOMATOES state (microprice logic)
        self.tom_ema = None
        self.tom_momentum = 0.0
        self.mid_history = []
        # EMERALDS uses fixed fair value, no state needed

    def run(self, state):
        orders = {}
        for symbol, depth in state.order_depths.items():
            if not depth.buy_orders or not depth.sell_orders:
                continue
            if symbol == "EMERALDS":
                orders[symbol] = self._emeralds(depth, state)
            elif symbol == "TOMATOES":
                orders[symbol] = self._tomatoes(depth, state)
        return orders, 0, ""

    def _emeralds(self, depth, state):
        """Taker penny logic for EMERALDS (proven best: 1050 platform PnL)."""
        bb = max(depth.buy_orders.keys())
        ba = min(depth.sell_orders.keys())
        pos = state.position.get("EMERALDS", 0)
        fair = 10000.0
        sym_orders = []
        # Take mispriced
        for p in sorted(depth.sell_orders.keys()):
            if p < fair - 2:
                sym_orders.append(Order("EMERALDS", p, min(abs(depth.sell_orders[p]), 10)))
        for p in sorted(depth.buy_orders.keys(), reverse=True):
            if p > fair + 2:
                sym_orders.append(Order("EMERALDS", p, -min(depth.buy_orders[p], 10)))
        # Always penny
        sym_orders.append(Order("EMERALDS", bb + 1, 12))
        sym_orders.append(Order("EMERALDS", ba - 1, -12))
        # Unwind
        if abs(pos) > 55:
            if pos > 0:
                sym_orders.append(Order("EMERALDS", bb, -min(20, pos)))
            else:
                sym_orders.append(Order("EMERALDS", ba, min(20, -pos)))
        return sym_orders

    def _tomatoes(self, depth, state):
        """Microprice sniper logic for TOMATOES (proven best: 1468 platform PnL)."""
        bb = max(depth.buy_orders.keys())
        ba = min(depth.sell_orders.keys())
        pos = state.position.get("TOMATOES", 0)
        # Unwind first
        if abs(pos) > 50:
            if pos > 0:
                return [Order("TOMATOES", bb, -min(20, pos))]
            else:
                return [Order("TOMATOES", ba, min(20, -pos))]
        # Microprice
        bid_vol = sum(depth.buy_orders.values())
        ask_vol = sum(-v for v in depth.sell_orders.values())
        total = bid_vol + ask_vol
        microprice = (bb * ask_vol + ba * bid_vol) / total if total > 0 else (bb + ba) / 2
        self.mid_history.append(microprice)
        self.mid_history = self.mid_history[-10:]
        # EMA fair value with momentum
        if self.tom_ema is None:
            self.tom_ema = microprice
        else:
            prev = self.tom_ema
            self.tom_ema = 0.15 * microprice + 0.85 * self.tom_ema
            self.tom_momentum = self.tom_ema - prev
        fair = self.tom_ema + self.tom_momentum * 0.3
        adj = fair - pos * 0.5
        sym_orders = []
        # Snipe mispriced
        if fair - 8 > bb:
            sym_orders.append(Order("TOMATOES", bb, min(15, 80 - pos)))
        if fair + 8 < ba:
            sym_orders.append(Order("TOMATOES", ba, -min(15, 80 + pos)))
        # Penny
        if ba - bb > 2:
            sym_orders.append(Order("TOMATOES", bb + 1, min(10, 80 - pos)))
            sym_orders.append(Order("TOMATOES", ba - 1, -min(10, 80 + pos)))
        return sym_orders
