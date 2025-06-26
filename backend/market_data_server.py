#backend/market_data_server
import grpc, time, concurrent.futures, random
from .order_book import OrderBook, Order, Trade
from .market_data_pb2_generated import market_data_pb2 as pb2
from .market_data_pb2_generated import market_data_pb2_grpc as pb2_grpc
import asyncio
from collections import defaultdict, deque
from typing import Optional, List
from dataclasses import dataclass, field
import threading

SERVER_ADDRESS = '[::]:50051'
SIMULATION_INTERVAL_SECONDS = 0.1
SIMULATION_ORDER_COUNT_PER_TICK = 1
MAX_ORDER_ID = 86400

SIMULATED_INSTRUMENTS: List[str] = ["BTC_USD","ETH_USD","XRP_USD","LTC_USD","BCH_USD","SOL_USD","ADA_USD",\
                                    "AVAX_USD","DOT_USD","DOGE_USD","MATIC_USD","SHIB_USD","LINK_USD","XLM_USD",\
                                    "TRX_USD","NEAR_USD","ETC_USD","FIL_USD","APT_USD","ARB_USD","SUI_USD",\
                                    "INJ_USD","OP_USD","PEPE_USD","FTM_USD","ALGO_USD","GRT_USD","IMX_USD",\
                                    "AAVE_USD","SNX_USD"]


_order_id_counter = 0
_order_id_lock = threading.Lock()

def get_next_order_id():
    global _order_id_counter
    with _order_id_lock:
        _order_id_counter += 1
        return _order_id_counter

class MarketDataServicer(pb2_grpc.MarketDataServiceServicer):
    def __init__(self):
        self.order_books: dict[str, OrderBook] = {}
        self.client_queues: defaultdict[str, list[asyncio.Queue]] = defaultdict(list)
        self.lock = threading.Lock()
        self.simulation_threads: dict[str, threading.Thread] = {}
        self.running_simulations: dict[str, bool] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None # Store reference to the event loop

        # Initialize and start simulations for all instrumets
        for instrument_id in SIMULATED_INSTRUMENTS:
            print(f"Setting up {instrument_id}")

            self.order_books[instrument_id] = OrderBook(
                instrument_id=instrument_id,
                on_market_update=self.on_market_update_callback
            )

            self.running_simulations[instrument_id] = True
            
            simulation_thread = threading.Thread(
                target=self._simulate_market_data,
                args=(instrument_id,),
                daemon=True
            )

            simulation_thread.start()
            self.simulation_threads[instrument_id] = simulation_thread
            time.sleep(0.05) # small pause btwn simulation starting
        print("All inintial simulations have started")

    # Async method to put response into queue
    async def _put_response_into_queue(self, instrument_id: str, response: pb2.MarketDataResponse):
        with self.lock:
            for client_queue in self.client_queues[instrument_id]:
                try:
                    # Await for the put operation, but with a timeout to avoid blocking indefinitely
                    # If you just use .put_nowait(), it can still fail silently if the queue is truly full
                    await asyncio.wait_for(client_queue.put(response), timeout=0.1) 
                except asyncio.QueueFull:
                    print(f"Warning: Client queue for {instrument_id} full, dropping update (async)")
                except asyncio.TimeoutError:
                    print(f"Warning: Client queue for {instrument_id} put timed out, dropping update (async)")


    def on_market_update_callback(self, instrument_id: str, price: float, quantity: int, side: bool, timestamp: float):
        """
        This callback runs in the simulation thread (synchronous context).
        It must safely submit an async task to the main event loop.
        """
        update_pb = pb2.OrderBookUpdate(
            instrument_id=instrument_id,
            price=price,
            quantity=quantity,
            side=side,
            timestamp=timestamp
        )
        response = pb2.MarketDataResponse(update=update_pb)

        if self.loop and self.loop.is_running():
            try:
                # Schedule the async coroutine to run on the main event loop
                asyncio.run_coroutine_threadsafe(
                    self._put_response_into_queue(instrument_id, response),
                    self.loop
                )
            except Exception as e:
                print(f"Error scheduling update for {instrument_id} on event loop: {e}")
        else:
            print(f"Warning: Event loop not running or not set, dropping update for {instrument_id}")

    def _simulate_market_data(self, instrument_id: str):
        print(f"Starting simulation for {instrument_id}...")
        side_choices = [True, False]

        current_on_market_update = self.order_books[instrument_id].on_market_update
        self.order_books[instrument_id].on_market_update = None

        print(f"Populating initial order book for {instrument_id}...")
        initial_price = round(random.uniform(50.0, 500.0),2)
        
        # Add initial bids (buy orders)
        for i in range(5):
            price = round(initial_price - (i * 0.1), 2)  # 100.0, 99.9, 99.8, 99.7, 99.6
            quantity = random.randint(5, 20)
            order = Order(
                order_id=get_next_order_id(),
                price=price,
                quantity=quantity,
                side=True,  # Buy
                order_type="limit"
            )
            self.order_books[instrument_id].add_order(order)
            # print(f"DEBUG: Added initial buy order - ID:{order.order_id} Price:{price} Qty:{quantity}") # Keep if needed for deep debug

        # Add initial asks (sell orders)
        for i in range(5):
            price = round(initial_price + 0.1 + (i * 0.1), 2)  # 100.1, 100.2, 100.3, 100.4, 100.5
            quantity = random.randint(5, 20)
            order = Order(
                order_id=get_next_order_id(),
                price=price,
                quantity=quantity,
                side=False,  # Sell
                order_type="limit"
            )
            self.order_books[instrument_id].add_order(order)
            # print(f"DEBUG: Added initial sell order - ID:{order.order_id} Price:{price} Qty:{quantity}") # Keep if needed for deep debug

        self.order_books[instrument_id].on_market_update = current_on_market_update
        time.sleep(0.1) # Small delay for initial orders to settle before first notification

        # Removed redundant initial book state print here, as snapshot will do it
        # current_book_state = self.order_books[instrument_id].dump_book()
        # print(f"DEBUG: Initial order book state:")
        # print(f"   Bids: {current_book_state['bids'][:3]}")
        # print(f"   Asks: {current_book_state['asks'][:3]}")

        # Signal that initial population is complete (if you had a proper signalling mechanism)
        # For now, the time.sleep in SubscribeMarketData still serves this simple purpose.

        # Continuous simulation
        while self.running_simulations[instrument_id]:
            try:
                for _ in range(SIMULATION_ORDER_COUNT_PER_TICK):
                    current_book = self.order_books[instrument_id].dump_book()
                    bids = current_book["bids"]
                    asks = current_book["asks"]

                    if bids and asks:
                        best_bid_price = bids[0][0]
                        best_ask_price = asks[0][0]
                        
                        if random.random() < 0.4:
                            price = best_ask_price if random.random() < 0.5 else best_bid_price
                        elif random.random() < 0.7:
                            spread = best_ask_price - best_bid_price
                            price = round(best_bid_price + random.uniform(0, spread), 2) if random.random() < 0.5 else round(best_ask_price - random.uniform(0, spread), 2)
                        else:
                            price = round(best_bid_price - random.uniform(0.1, 0.5), 2) if random.random() < 0.5 else round(best_ask_price + random.uniform(0.1, 0.5), 2)
                        
                        price = max(0.01, price)
                    else:
                        price = round(random.uniform(99.0, 101.0), 2)

                    quantity = random.randint(1, 15)
                    side = random.choice(side_choices)
                    
                    order_type = "limit" if random.random() < 0.8 else "market"

                    order = Order(
                        order_id=get_next_order_id(),
                        price=price,
                        quantity=quantity,
                        side=side,
                        order_type=order_type
                    )
                    self.order_books[instrument_id].add_order(order)

                time.sleep(SIMULATION_INTERVAL_SECONDS)
            except Exception as e:
                print(f"Error in simulation loop for {instrument_id}: {e}")
                time.sleep(1)
        
        print(f"Stopping simulation for {instrument_id}...")

    async def SubscribeMarketData(self, request: pb2.SubscriptionRequest, context: grpc.aio.ServicerContext):
        instrument_id = request.instrument_id
        client_queue = asyncio.Queue()

        # Set the event loop reference the first time it's needed
        if self.loop is None:
            self.loop = asyncio.get_running_loop() # Get the current event loop

        with self.lock:
            if instrument_id not in self.order_books:
                print(f"First subscription for {instrument_id}. Creating OrderBook and starting simulation.")
                self.order_books[instrument_id] = OrderBook(
                    instrument_id=instrument_id,
                    on_market_update=self.on_market_update_callback
                )
                self.running_simulations[instrument_id] = True
                
                simulation_thread = threading.Thread(
                    target=self._simulate_market_data,
                    args=(instrument_id,),
                    daemon=True
                )
                simulation_thread.start()
                self.simulation_threads[instrument_id] = simulation_thread
                
                time.sleep(0.2) # Give simulation a moment to populate initial book
            
            self.client_queues[instrument_id].append(client_queue)
            print(f"Client subscribed to {instrument_id}. Total subscribers: {len(self.client_queues[instrument_id])}")

        try:
            snapshot_data = self.order_books[instrument_id].dump_book()
            # print(f"DEBUG: Sending snapshot with {len(snapshot_data['bids'])} bids and {len(snapshot_data['asks'])} asks") # Keep if needed for debug
            
            bids_pb = [pb2.OrderBookLevel(price=p, quantity=q) for p, q in snapshot_data["bids"]]
            asks_pb = [pb2.OrderBookLevel(price=p, quantity=q) for p, q in snapshot_data["asks"]]

            snapshot_pb = pb2.OrderBookSnapshot(
                instrument_id=instrument_id,
                bids=bids_pb,
                asks=asks_pb,
                timestamp=time.time()
            )
            initial_response = pb2.MarketDataResponse(snapshot=snapshot_pb)
            yield initial_response

            # Stream updates
            while True:
                response = await client_queue.get() # This should now receive updates
                yield response

        except grpc.RpcError as e:
            print(f"Client for {instrument_id} disconnected or RPC error: {e}")
        except asyncio.CancelledError:
            print(f"Client for {instrument_id} stream cancelled.")
        finally:
            with self.lock:
                if client_queue in self.client_queues[instrument_id]:
                    self.client_queues[instrument_id].remove(client_queue)
                print(f"Client unsubscribed from {instrument_id}. Remaining subscribers: {len(self.client_queues[instrument_id])}")
                
                if not self.client_queues[instrument_id] and instrument_id in self.running_simulations:
                    print(f"No more subscribers for {instrument_id}. Stopping simulation.")
                    self.running_simulations[instrument_id] = False

async def serve():
    server = grpc.aio.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    servicer_instance = MarketDataServicer()
    pb2_grpc.add_MarketDataServiceServicer_to_server(servicer_instance, server)
    server.add_insecure_port(SERVER_ADDRESS)
    print(f"Server listening on {SERVER_ADDRESS}")
    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        print("Server shutting down...")
        await server.stop(grace=5)

if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("Server process interrupted.")