# backend/market_data_client.py
import grpc.aio
from .market_data_pb2_generated import market_data_pb2 as pb2 # Unused now directly here
from .market_data_pb2_generated import market_data_pb2_grpc as pb2_grpc
import asyncio
import grpc
import random, time

# IMPORT THE NEW ClientOrderBook from the model file
from .market_data_model import ClientOrderBook # <--- NEW IMPORT

SERVER_ADDRESS = 'localhost:50051'

async def subscribe_to_market_data(instrument_id: str):
    # Initialize a ClientOrderBook for this specific instrument
    client_order_book = ClientOrderBook(instrument_id)

    async with grpc.aio.insecure_channel(SERVER_ADDRESS) as channel:
        stub = pb2_grpc.MarketDataServiceStub(channel)
        print(f"CLI Client for {instrument_id}: Subscribing to market data...")
        
        request = pb2.market_data_pb2.SubscriptionRequest(instrument_id=instrument_id) # Refer to pb2 via its full path
        
        try:
            response_iterator = stub.SubscribeMarketData(request)
            async for response in response_iterator:
                if response.HasField('snapshot'):
                    snapshot_data = response.snapshot
                    client_order_book.apply_snapshot(snapshot_data)
                    print(client_order_book.display_book())

                elif response.HasField('update'):
                    update_data = response.update
                    client_order_book.apply_update(update_data)
                    
                    print(f"CLI Client for {instrument_id}: Applied update {update_data.price:.2f}@{update_data.quantity} ({'BUY' if update_data.side else 'SELL'})")
                    print(client_order_book.display_book())

                else:
                    print(f"CLI Client for {instrument_id}: Received MarketDataResponse with no recognized field set.")
        
        except grpc.aio.AioRpcError as e:
            print(f"CLI Client for {instrument_id}: RPC Error occurred: {e.code()} - {e.details()}")
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                print(f"CLI Client for {instrument_id}: Server is unavailable. Make sure the server is running.")
            elif e.code() == grpc.StatusCode.CANCELLED:
                print(f"CLI Client for {instrument_id}: Stream cancelled by client or server.")
            elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                print(f"CLI Client for {instrument_id}: Operation timed out.")
            else:
                print(f"CLI Client for {instrument_id}: An unexpected gRPC error occurred: {e}")
        except asyncio.CancelledError:
            print(f"CLI Client task for {instrument_id} was cancelled (e.g., by KeyboardInterrupt).")
        except Exception as e:
            print(f"CLI Client for {instrument_id}: An unexpected error occurred in client stream: {e}")

async def main():
    # Make sure this list matches SIMULATED_INSTRUMENTS in your server for full testing
    instruments_to_subscribe = ["BTC_USD","ETH_USD","XRP_USD","LTC_USD","BCH_USD","SOL_USD","ADA_USD",
                                 "AVAX_USD","DOT_USD","DOGE_USD","MATIC_USD","SHIB_USD","LINK_USD","XLM_USD",
                                 "TRX_USD","NEAR_USD","ETC_USD","FIL_USD","APT_USD","ARB_USD","SUI_USD",
                                 "INJ_USD","OP_USD","PEPE_USD","FTM_USD","ALGO_USD","GRT_USD","IMX_USD",
                                 "AAVE_USD","SNX_USD"]
    
    tasks = []
    print("Starting CLI client subscriptions...")
    for instrument_id in instruments_to_subscribe:
        tasks.append(asyncio.create_task(subscribe_to_market_data(instrument_id)))
        # Stagger subscription initiation
        await asyncio.sleep(random.uniform(0.3, 1.5))
        
    await asyncio.gather(*tasks)
            
if __name__ == '__main__':    
    try:
        # NOTE: Make sure the gRPC server (market_data_server.py) is running before starting this client.
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCLI Client stopped by user (KeyboardInterrupt).")
    except Exception as e:
        print(f"Error running CLI client: {e}")