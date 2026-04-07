"""Skewed taker penny — Gemini R2 + sweep (order_size=10)."""
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
        self.ema_values = {}
    def run(self, state):
        orders = {}
        for symbol, depth in state.order_depths.items():
            if not depth.buy_orders or not depth.sell_orders: continue
            bb = max(depth.buy_orders.keys())
            ba = min(depth.sell_orders.keys())
            pos = state.position.get(symbol, 0)
            if symbol == "EMERALDS": fair = 10000.0
            else:
                mid = (bb+ba)/2
                if symbol not in self.ema_values: self.ema_values[symbol] = mid
                self.ema_values[symbol] = 0.1*mid + 0.9*self.ema_values[symbol]
                fair = self.ema_values[symbol]
            skew = pos * 0.3
            skewed_fair = fair - skew
            orders[symbol] = []
            remaining_buy = 80 - pos
            remaining_sell = 80 + pos
            # Unwind
            if abs(pos) >= 60:
                if pos > 0 and remaining_sell > 0:
                    orders[symbol].append(Order(symbol, bb, -min(10, remaining_sell)))
                elif pos < 0 and remaining_buy > 0:
                    orders[symbol].append(Order(symbol, ba, min(10, remaining_buy)))
            # Take
            if ba <= skewed_fair - 2 and remaining_buy > 0:
                orders[symbol].append(Order(symbol, ba, min(10, remaining_buy)))
            if bb >= skewed_fair + 2 and remaining_sell > 0:
                orders[symbol].append(Order(symbol, bb, -min(10, remaining_sell)))
            # Penny
            if remaining_buy > 0:
                orders[symbol].append(Order(symbol, bb+1, min(10, remaining_buy)))
            if remaining_sell > 0:
                orders[symbol].append(Order(symbol, ba-1, -min(10, remaining_sell)))
        return orders, 0, ""
