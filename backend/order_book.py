#backend/order_book.py
import time
import heapq
from dataclasses import dataclass, field
from typing import List, Optional, Callable

@dataclass
class Order:
    order_id: int
    price: float
    quantity: int
    side: bool      # True for buy, False for sell
    order_type: str # "limit" or "market"
    timestamp: float = field(default_factory=time.time)
    
    def __lt__(self, other):
        """Custom comparison for heap ordering"""
        if self.side:  # Buy orders - higher price has priority (max heap behavior)
            if self.price != other.price:
                return self.price > other.price  # Higher price comes first
            return self.timestamp < other.timestamp  # Earlier timestamp breaks ties
        else:  # Sell orders - lower price has priority (min heap behavior)
            if self.price != other.price:
                return self.price < other.price  # Lower price comes first
            return self.timestamp < other.timestamp  # Earlier timestamp breaks ties

@dataclass
class Trade:
    buy_order_id: int
    sell_order_id: int
    price: float
    quantity: int
    timestamp: float = field(default_factory=time.time)

class OrderBook:
    def __init__(self, instrument_id: str, on_market_update: Optional[Callable] = None):
        self.instrument_id = instrument_id
        self.buy_heap: List[Order] = []
        self.sell_heap: List[Order] = []
        self.trade_log: List[Trade] = []
        self.on_market_update = on_market_update

    def _notify_update(self, price: float, quantity: int, side: bool):
        """Internal helper to call the external update callback."""
        if self.on_market_update:
            self.on_market_update(self.instrument_id, price, quantity, side, time.time())

    def add_order(self, order: Order):
        print(f"DEBUG: Adding order: ID={order.order_id}, Price={order.price}, Qty={order.quantity}, Side={'BUY' if order.side else 'SELL'}, Type={order.order_type}")

        if order.side:  # Buy order
            self._match_buy(order)
            if order.quantity > 0 and order.order_type == "limit":
                heapq.heappush(self.buy_heap, order)
                print(f"DEBUG: Pushed buy limit order {order.order_id} to buy_heap. Current buy_heap size: {len(self.buy_heap)}")
            else:
                print(f"DEBUG: Buy order {order.order_id} not pushed to heap. Qty={order.quantity}, Type={order.order_type}")
        else:  # Sell order
            self._match_sell(order)
            if order.quantity > 0 and order.order_type == "limit":
                heapq.heappush(self.sell_heap, order)
                print(f"DEBUG: Pushed sell limit order {order.order_id} to sell_heap. Current sell_heap size: {len(self.sell_heap)}")
            else:
                print(f"DEBUG: Sell order {order.order_id} not pushed to heap. Qty={order.quantity}, Type={order.order_type}")

    def _match_buy(self, buy_order: Order):
        while buy_order.quantity > 0 and self.sell_heap:
            best_sell = self.sell_heap[0]
            
            # For limit orders, check price compatibility
            if buy_order.order_type == "limit" and best_sell.price > buy_order.price:
                break
            
            trade_qty = min(buy_order.quantity, best_sell.quantity)
            trade_price = best_sell.price
            
            # Create trade
            trade = Trade(
                buy_order_id=buy_order.order_id,
                sell_order_id=best_sell.order_id,
                price=trade_price,
                quantity=trade_qty
            )
            self.trade_log.append(trade)
            
            # Update quantities
            buy_order.quantity -= trade_qty
            best_sell.quantity -= trade_qty
            
            print(f"DEBUG: Trade executed - Buy:{buy_order.order_id} Sell:{best_sell.order_id} Price:{trade_price} Qty:{trade_qty}")
            
            # Handle sell order after trade
            if best_sell.quantity == 0:
                heapq.heappop(self.sell_heap)
                self._notify_update(best_sell.price, 0, False)  # Notify level removed
                print(f"DEBUG: Sell order {best_sell.order_id} fully filled and removed from heap")
            else:
                self._notify_update(best_sell.price, best_sell.quantity, False)  # Notify quantity change

    def _match_sell(self, sell_order: Order):
        while sell_order.quantity > 0 and self.buy_heap:
            best_buy = self.buy_heap[0]
            
            # For limit orders, check price compatibility
            if sell_order.order_type == "limit" and best_buy.price < sell_order.price:
                break
            
            trade_qty = min(sell_order.quantity, best_buy.quantity)
            trade_price = best_buy.price
            
            # Create trade
            trade = Trade(
                buy_order_id=best_buy.order_id,
                sell_order_id=sell_order.order_id,
                price=trade_price,
                quantity=trade_qty
            )
            self.trade_log.append(trade)
            
            # Update quantities
            sell_order.quantity -= trade_qty
            best_buy.quantity -= trade_qty
            
            print(f"DEBUG: Trade executed - Buy:{best_buy.order_id} Sell:{sell_order.order_id} Price:{trade_price} Qty:{trade_qty}")
            
            # Handle buy order after trade
            if best_buy.quantity == 0:
                heapq.heappop(self.buy_heap)
                self._notify_update(best_buy.price, 0, True)  # Notify level removed
                print(f"DEBUG: Buy order {best_buy.order_id} fully filled and removed from heap")
            else:
                self._notify_update(best_buy.price, best_buy.quantity, True)  # Notify quantity change

    def get_best_bid(self) -> Optional[Order]:
        return self.buy_heap[0] if self.buy_heap else None

    def get_best_ask(self) -> Optional[Order]:
        return self.sell_heap[0] if self.sell_heap else None

    def get_trade_log(self) -> List[Trade]:
        return self.trade_log

    def dump_book(self) -> dict:
        print(f"DEBUG: dump_book called. Buy Heap size: {len(self.buy_heap)}, Sell Heap size: {len(self.sell_heap)}")
        
        # Aggregate orders by price level
        buy_levels = {}
        sell_levels = {}
        
        # Process buy orders
        for order in self.buy_heap:
            if order.price in buy_levels:
                buy_levels[order.price] += order.quantity
            else:
                buy_levels[order.price] = order.quantity
        
        # Process sell orders
        for order in self.sell_heap:
            if order.price in sell_levels:
                sell_levels[order.price] += order.quantity
            else:
                sell_levels[order.price] = order.quantity
        
        # Sort and format
        bids = [(price, qty) for price, qty in sorted(buy_levels.items(), reverse=True)]
        asks = [(price, qty) for price, qty in sorted(sell_levels.items())]
        
        print(f"DEBUG: Returning bids: {bids[:5]}")  # Show first 5 levels
        print(f"DEBUG: Returning asks: {asks[:5]}")  # Show first 5 levels
        
        return {
            "bids": bids,
            "asks": asks
        }