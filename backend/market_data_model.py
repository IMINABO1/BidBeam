# backend/market_data_model.py
import heapq
from typing import Dict, List, Tuple, Optional

# Import generated protobuf types if needed for type hinting, though not strictly required for the class itself
# from .market_data_pb2_generated import market_data_pb2 as pb2


class ClientOrderBook:
    """
    Maintains a local, in-memory representation of an order book for a single instrument.
    This class is reusable by different clients (CLI, Web).
    """
    def __init__(self, instrument_id: str):
        self.instrument_id = instrument_id
        self.bids: Dict[float, int] = {}
        self._bid_heap: List[Tuple[float, float]] = [] # (-price, price)
        self.asks: Dict[float, int] = {}
        self._ask_heap: List[Tuple[float, float]] = [] # (price, price)
        self.last_update_timestamp: float = 0.0

    # Note: For apply_snapshot and apply_update, you'll need to pass the protobuf messages
    # as arguments. I'll include type hints assuming you pass the raw protobuf objects.
    # If you prefer to pass parsed dicts, you can adjust the methods.
    # For now, I'll keep using pb2 objects for direct compatibility.

    def apply_snapshot(self, snapshot): # type: (Any) -> None # Using Any for protobuf for simplicity here
        """
        Applies a full order book snapshot, clearing existing data.
        Expects a pb2.OrderBookSnapshot object.
        """
        self.bids.clear()
        self.asks.clear()
        self._bid_heap = []
        self._ask_heap = []

        for level in snapshot.bids:
            self.bids[level.price] = level.quantity
            heapq.heappush(self._bid_heap, (-level.price, level.price))

        for level in snapshot.asks:
            self.asks[level.price] = level.quantity
            heapq.heappush(self._ask_heap, (level.price, level.price))

        self.last_update_timestamp = snapshot.timestamp

    def apply_update(self, update): # type: (Any) -> None # Using Any for protobuf for simplicity here
        """
        Applies an incremental order book update.
        Expects a pb2.OrderBookUpdate object.
        """
        target_dict = self.bids if update.side else self.asks
        target_heap = self._bid_heap if update.side else self._ask_heap

        if update.quantity > 0:
            if update.price not in target_dict:
                heapq.heappush(target_heap, (-update.price, update.price) if update.side else (update.price, update.price))
            target_dict[update.price] = update.quantity
        else:
            if update.price in target_dict:
                del target_dict[update.price]
        self.last_update_timestamp = update.timestamp

    def get_best_bid(self) -> Tuple[Optional[float], Optional[int]]:
        while self._bid_heap:
            _, price = self._bid_heap[0]
            if price in self.bids and self.bids[price] > 0:
                return price, self.bids[price]
            heapq.heappop(self._bid_heap)
        return None, None

    def get_best_ask(self) -> Tuple[Optional[float], Optional[int]]:
        while self._ask_heap:
            _, price = self._ask_heap[0]
            if price in self.asks and self.asks[price] > 0:
                return price, self.asks[price]
            heapq.heappop(self._ask_heap)
        return None, None

    def get_top_n_levels_list(self, n=5) -> Tuple[List[Dict], List[Dict]]:
        """
        Returns the top N bid and ask levels as sorted lists of dictionaries 
        (e.g., [{"price": p, "quantity": q}, ...]).
        """
        # Ensure quantities are positive before sorting
        sorted_bids = sorted([ (p, q) for p, q in self.bids.items() if q > 0 ], key=lambda x: x[0], reverse=True)[:n]
        sorted_asks = sorted([ (p, q) for p, q in self.asks.items() if q > 0 ], key=lambda x: x[0])[:n]
        
        # Convert to list of dicts for easier JSON serialization
        bids_dicts = [{"price": p, "quantity": q} for p, q in sorted_bids]
        asks_dicts = [{"price": p, "quantity": q} for p, q in sorted_asks]
        
        return bids_dicts, asks_dicts

    def display_book(self):
        """Prints a formatted view of the order book for CLI display."""
        best_bid_price, best_bid_qty = self.get_best_bid()
        best_ask_price, best_ask_qty = self.get_best_ask()
        
        bids_list, asks_list = self.get_top_n_levels_list(n=5) # Get top 5 levels for CLI
        
        display_str = f"\n--- {self.instrument_id} Order Book (Timestamp: {self.last_update_timestamp:.2f}) ---\n"
        display_str += f"Best Bid: {best_bid_price:.2f} @ {best_bid_qty} | Best Ask: {best_ask_price:.2f} @ {best_ask_qty}\n"
        display_str += "--------------------------------------------------\n"
        
        display_str += "Asks:\n"
        for level in reversed(asks_list): # Reverse for display: highest price first for asks
            display_str += f"  {level['price']:10.2f} {level['quantity']:>10}\n"
        
        display_str += "--------------------------------------------------\n"
        display_str += "Bids:\n"
        for level in bids_list:
            display_str += f"  {level['price']:10.2f} {level['quantity']:>10}\n"
        
        display_str += "--------------------------------------------------\n"
        return display_str
    
    def to_dict(self) -> Dict:
        """Converts the current order book state to a dictionary for JSON serialization (web)."""
        bids_list, asks_list = self.get_top_n_levels_list(n=10) # Get more levels for web display
        best_bid_price, best_bid_qty = self.get_best_bid()
        best_ask_price, best_ask_qty = self.get_best_ask()

        return {
            "instrument_id": self.instrument_id,
            "timestamp": self.last_update_timestamp,
            "best_bid": {"price": best_bid_price, "quantity": best_bid_qty} if best_bid_price is not None else None,
            "best_ask": {"price": best_ask_price, "quantity": best_ask_qty} if best_ask_price is not None else None,
            "bids": bids_list,
            "asks": asks_list
        }