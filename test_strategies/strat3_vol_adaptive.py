"""Vol-adaptive wider spread MM."""
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
        self.ema = {}
        self.history = {}
    def run(self, state):
        orders = {}
        for sym, depth in state.order_depths.items():
            if not depth.buy_orders or not depth.sell_orders: continue
            bb, ba = max(depth.buy_orders.keys()), min(depth.sell_orders.keys())
            mid = (bb+ba)/2; pos = state.position.get(sym, 0)
            if sym not in self.history: self.history[sym] = []
            self.history[sym].append(mid); self.history[sym] = self.history[sym][-20:]
            vol = 1.0
            if len(self.history[sym]) > 2:
                avg = sum(self.history[sym])/len(self.history[sym])
                vol = max(1, math.sqrt(sum((p-avg)**2 for p in self.history[sym])/len(self.history[sym])))
            spread = max(3, int(vol * 2))
            fair = 10000.0 if sym == "EMERALDS" else mid
            skew = int(pos * 0.4)
            orders[sym] = [Order(sym, int(fair)-spread-skew, 12), Order(sym, int(fair)+spread-skew, -12)]
            if abs(pos) > 55:
                if pos > 0: orders[sym].append(Order(sym, bb, -20))
                else: orders[sym].append(Order(sym, ba, 20))
        return orders, 0, ""
