"""Aggressive taker + always penny."""

Time = int
Symbol = str
Product = str
Position = int
UserId = str
ObservationValue = int


class Listing:
    def __init__(s, symbol, product, denomination):
        s.symbol = symbol
        s.product = product
        s.denomination = denomination


class ConversionObservation:
    def __init__(
        s, bidPrice, askPrice, transportFees, exportTariff, importTariff, sugarPrice, sunlightIndex
    ):
        s.bidPrice = bidPrice
        s.askPrice = askPrice
        s.transportFees = transportFees
        s.exportTariff = exportTariff
        s.importTariff = importTariff
        s.sugarPrice = sugarPrice
        s.sunlightIndex = sunlightIndex


class Observation:
    def __init__(s, plainValueObservations=None, conversionObservations=None):
        s.plainValueObservations = plainValueObservations or {}
        s.conversionObservations = conversionObservations or {}


class Order:
    def __init__(s, symbol, price, quantity):
        s.symbol = symbol
        s.price = price
        s.quantity = quantity


class OrderDepth:
    def __init__(s):
        s.buy_orders = {}
        s.sell_orders = {}


class Trade:
    def __init__(s, symbol, price, quantity, buyer="", seller="", timestamp=0):
        s.symbol = symbol
        s.price = price
        s.quantity = quantity
        s.buyer = buyer
        s.seller = seller
        s.timestamp = timestamp


class TradingState:
    def __init__(
        s,
        timestamp,
        traderData,
        listings,
        order_depths,
        own_trades,
        market_trades,
        position,
        observations,
    ):
        s.timestamp = timestamp
        s.traderData = traderData
        s.listings = listings
        s.order_depths = order_depths
        s.own_trades = own_trades
        s.market_trades = market_trades
        s.position = position
        s.observations = observations


class Trader:
    def __init__(self):
        self.ema = {}

    def run(self, state):
        orders = {}
        for sym, depth in state.order_depths.items():
            if not depth.buy_orders or not depth.sell_orders:
                continue
            bb, ba = max(depth.buy_orders.keys()), min(depth.sell_orders.keys())
            pos = state.position.get(sym, 0)
            mid = (bb + ba) / 2
            fair = 10000.0 if sym == "EMERALDS" else mid
            if sym != "EMERALDS":
                if sym not in self.ema:
                    self.ema[sym] = mid
                self.ema[sym] = 0.2 * mid + 0.8 * self.ema[sym]
                fair = self.ema[sym]
            sym_orders = []
            for p in sorted(depth.sell_orders.keys()):
                if p < fair - 2:
                    sym_orders.append(Order(sym, p, min(abs(depth.sell_orders[p]), 10)))
            for p in sorted(depth.buy_orders.keys(), reverse=True):
                if p > fair + 2:
                    sym_orders.append(Order(sym, p, -min(depth.buy_orders[p], 10)))
            sym_orders.append(Order(sym, bb + 1, 12))
            sym_orders.append(Order(sym, ba - 1, -12))
            if abs(pos) > 55:
                if pos > 0:
                    sym_orders.append(Order(sym, bb, -20))
                else:
                    sym_orders.append(Order(sym, ba, 20))
            orders[sym] = sym_orders
        return orders, 0, ""
