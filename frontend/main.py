# frontend/main.py
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import grpc.aio
from collections import defaultdict
import json
import time
from typing import Dict, List, Tuple, Optional, Any

# IMPORT THE NEW ClientOrderBook from the model file
from backend.market_data_model import ClientOrderBook # <--- NEW IMPORT

# Import generated protobuf files
from backend.market_data_pb2_generated import market_data_pb2 as pb2
from backend.market_data_pb2_generated import market_data_pb2_grpc as pb2_grpc

# --- Configuration ---
SERVER_ADDRESS = 'localhost:50051' # Your gRPC server address
# List of instruments to subscribe to from the gRPC server
# Make sure this matches SIMULATED_INSTRUMENTS in your market_data_server.py
INSTRUMENTS_TO_SUBSCRIBE = [
    "BTC_USD", "ETH_USD", "XRP_USD", "LTC_USD", "BCH_USD", "SOL_USD", "ADA_USD",
    "AVAX_USD", "DOT_USD", "DOGE_USD", "MATIC_USD", "SHIB_USD", "LINK_USD", "XLM_USD",
    "TRX_USD", "NEAR_USD", "ETC_USD", "FIL_USD", "APT_USD", "ARB_USD", "SUI_USD",
    "INJ_USD", "OP_USD", "PEPE_USD", "FTM_USD", "ALGO_USD", "GRT_USD", "IMX_USD",
    "AAVE_USD", "SNX_USD"
]

# --- FastAPI App Setup ---
app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# --- Global State for Market Data (shared across requests and tasks) ---
# Stores the current reconstructed order book for each instrument
# {instrument_id: ClientOrderBook_instance}
global_order_books: Dict[str, ClientOrderBook] = {}
# Stores active WebSocket connections for broadcasting
# {instrument_id: [WebSocket_connection_1, WebSocket_connection_2, ...]}
active_websocket_connections: defaultdict[str, List[WebSocket]] = defaultdict(list)


# --- gRPC Subscription Task ---
async def subscribe_to_grpc_market_data(instrument_id: str):
    """
    Subscribes to the gRPC server for a single instrument and updates global state.
    Broadcasts updates via WebSockets.
    """
    global_order_books[instrument_id] = ClientOrderBook(instrument_id)
    
    async with grpc.aio.insecure_channel(SERVER_ADDRESS) as channel:
        stub = pb2_grpc.MarketDataServiceStub(channel)
        print(f"FastAPI gRPC Client for {instrument_id}: Subscribing to market data...")
        
        request = pb2.SubscriptionRequest(instrument_id=instrument_id)
        
        try:
            response_iterator = stub.SubscribeMarketData(request)
            async for response in response_iterator:
                if response.HasField('snapshot'):
                    snapshot_data = response.snapshot
                    global_order_books[instrument_id].apply_snapshot(snapshot_data)
                    # When a snapshot arrives, also send the current full state to all connected websockets
                    await broadcast_market_data(instrument_id)

                elif response.HasField('update'):
                    update_data = response.update
                    global_order_books[instrument_id].apply_update(update_data)
                    # After applying update, broadcast the updated full state
                    await broadcast_market_data(instrument_id)

        except grpc.aio.AioRpcError as e:
            print(f"FastAPI gRPC Client for {instrument_id}: RPC Error occurred: {e.code()} - {e.details()}")
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                print(f"FastAPI gRPC Client for {instrument_id}: Server is unavailable. Retrying in 5 seconds...")
                await asyncio.sleep(5)
                # Re-run the subscription task if disconnected
                asyncio.create_task(subscribe_to_grpc_market_data(instrument_id)) 
            else:
                print(f"FastAPI gRPC Client for {instrument_id}: An unexpected gRPC error occurred: {e}")
        except asyncio.CancelledError:
            print(f"FastAPI gRPC Client task for {instrument_id} was cancelled.")
        except Exception as e:
            print(f"FastAPI gRPC Client for {instrument_id}: An unexpected error occurred in gRPC stream: {e}")

async def broadcast_market_data(instrument_id: str):
    """
    Sends the current order book state for an instrument to all connected WebSockets
    subscribed to that instrument.
    """
    if instrument_id in global_order_books:
        current_book_data = global_order_books[instrument_id].to_dict()
        message = json.dumps(current_book_data)
        
        # Iterate over a copy of the list, as it might be modified during iteration
        for connection in list(active_websocket_connections[instrument_id]):
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                print(f"WebSocket client for {instrument_id} disconnected during broadcast.")
                active_websocket_connections[instrument_id].remove(connection)
            except Exception as e:
                print(f"Error broadcasting to WebSocket for {instrument_id}: {e}")
                active_websocket_connections[instrument_id].remove(connection)


# --- FastAPI Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """
    On FastAPI startup, kick off the background gRPC client tasks for all instruments.
    """
    print("FastAPI application startup: Starting gRPC subscriptions...")
    for instrument_id in INSTRUMENTS_TO_SUBSCRIBE:
        asyncio.create_task(subscribe_to_grpc_market_data(instrument_id))
        await asyncio.sleep(0.1) 
    print("FastAPI application startup: gRPC subscription tasks initiated.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    On FastAPI shutdown, perform cleanup.
    """
    print("FastAPI application shutdown: Closing all WebSocket connections.")
    for instrument_id in active_websocket_connections:
        for connection in active_websocket_connections[instrument_id]:
            try:
                await connection.close()
            except RuntimeError: # Already closed
                pass
    print("FastAPI application shutdown complete.")


# --- HTTP Endpoint (for serving HTML) ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Serves the main HTML page.
    """
    return templates.TemplateResponse("index.html", {"request": request})

# --- WebSocket Endpoint (for real-time market data) ---
@app.websocket("/ws/market_data/{instrument_id}")
async def websocket_endpoint(websocket: WebSocket, instrument_id: str):
    """
    Handles WebSocket connections for a specific instrument.
    """
    await websocket.accept()
    print(f"WebSocket client connected for {instrument_id}")

    active_websocket_connections[instrument_id].append(websocket)

    try:
        # Send initial snapshot immediately upon connection
        if instrument_id in global_order_books:
            initial_data = global_order_books[instrument_id].to_dict()
            await websocket.send_text(json.dumps(initial_data))
            print(f"Sent initial snapshot for {instrument_id} to new WebSocket client.")
        else:
            await websocket.send_text(json.dumps({"error": f"No data yet for {instrument_id}"}))

        while True:
            # We don't expect messages *from* the client for market data display,
            # but this keeps the connection alive.
            data = await websocket.receive_text()
            print(f"Received message from WebSocket for {instrument_id}: {data}")

    except WebSocketDisconnect:
        print(f"WebSocket client for {instrument_id} disconnected.")
    except Exception as e:
        print(f"WebSocket error for {instrument_id}: {e}")
    finally:
        if websocket in active_websocket_connections[instrument_id]:
            active_websocket_connections[instrument_id].remove(websocket)