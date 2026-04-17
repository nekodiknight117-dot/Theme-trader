import os
import json
import asyncio
from alpaca_trade_api.stream import Stream
from fastapi import WebSocket

# Keep track of active websocket connections
active_connections = []

async def broadcast_price_update(msg):
    """
    Broadcast the price update to all connected frontend WebSockets
    """
    if not active_connections:
        return
        
    data = {
        "ticker": msg.symbol,
        "price": msg.price,
        "timestamp": str(msg.timestamp)
    }
    
    # We need to broadcast safely without blocking the stream
    for connection in active_connections:
        try:
            await connection.send_text(json.dumps(data))
        except Exception as e:
            active_connections.remove(connection)

async def start_alpaca_stream(tickers=["AAPL", "SPY", "NVDA"]):
    """
    Start the Alpaca WebSocket stream for real-time trade data
    """
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    
    if not api_key or not secret_key:
        print("Warning: Alpaca API keys not found. Live streaming will not work.")
        return

    # Using the IEX data feed which is free for paper trading accounts
    stream = Stream(api_key, secret_key, base_url="https://paper-api.alpaca.markets", data_feed='iex')

    # Handler for trade updates
    async def trade_callback(t):
        await broadcast_price_update(t)

    # Subscribe to trades for the given tickers
    stream.subscribe_trades(trade_callback, *tickers)

    # Start the stream in the background
    print(f"Starting Alpaca stream for {tickers}")
    try:
        await stream._run_forever()
    except Exception as e:
        print(f"Alpaca stream error: {e}")
