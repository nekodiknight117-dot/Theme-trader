import os
import json
import asyncio
import logging
from pathlib import Path

import websockets
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Load root .env so keys are available regardless of launch directory
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
try:
    import dotenv
    dotenv.load_dotenv(dotenv_path=_ROOT_ENV, override=True)
except ImportError:
    pass

# Active frontend WebSocket connections (managed by the /ws/prices endpoint)
active_connections: list[WebSocket] = []

# Alpaca market data WebSocket URL (IEX free feed)
_ALPACA_WS_URL = "wss://stream.data.alpaca.markets/v2/iex"

# Tickers to stream
DEFAULT_TICKERS = ["AAPL", "SPY", "NVDA"]

# Internal cancellation flag for clean shutdown
_stream_task: asyncio.Task | None = None


async def _broadcast(data: dict) -> None:
    """Send a price update to all connected frontend WebSockets."""
    if not active_connections:
        return
    message = json.dumps(data)
    dead = []
    for ws in active_connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_connections.remove(ws)


async def _run_stream(api_key: str, secret_key: str, tickers: list[str]) -> None:
    """
    Connect to Alpaca's market data WebSocket, authenticate, subscribe to
    real-time trades, and broadcast updates to frontend clients.
    Reconnects automatically on transient errors.
    """
    while True:
        try:
            async with websockets.connect(_ALPACA_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                # Step 1: receive the welcome message
                await ws.recv()

                # Step 2: authenticate
                auth = {"action": "auth", "key": api_key, "secret": secret_key}
                await ws.send(json.dumps(auth))
                auth_resp = json.loads(await ws.recv())
                if auth_resp[0].get("msg") != "authenticated":
                    logger.error("[alpaca_stream] Authentication failed: %s", auth_resp)
                    await asyncio.sleep(10)
                    continue

                # Step 3: subscribe to trades
                sub = {"action": "subscribe", "trades": tickers}
                await ws.send(json.dumps(sub))
                logger.info("[alpaca_stream] Subscribed to trades: %s", tickers)

                # Step 4: receive and broadcast messages
                async for raw in ws:
                    messages = json.loads(raw)
                    for msg in messages:
                        if msg.get("T") == "t":  # trade event
                            await _broadcast({
                                "ticker":    msg.get("S"),
                                "price":     msg.get("p"),
                                "timestamp": msg.get("t"),
                            })

        except asyncio.CancelledError:
            logger.info("[alpaca_stream] Stream cancelled — shutting down cleanly.")
            return
        except Exception as e:
            logger.warning("[alpaca_stream] Connection error: %s — reconnecting in 5s", e)
            await asyncio.sleep(5)


async def start_alpaca_stream(tickers: list[str] = DEFAULT_TICKERS) -> None:
    """
    Entry point called from main.py lifespan. Starts the stream task and
    stores a reference so it can be cancelled on shutdown.
    """
    global _stream_task

    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")

    if not api_key or not secret_key:
        logger.warning(
            "[alpaca_stream] ALPACA_API_KEY or ALPACA_SECRET_KEY not set. "
            "Live price streaming is disabled."
        )
        return

    logger.info("[alpaca_stream] Starting Alpaca market data stream for %s", tickers)
    _stream_task = asyncio.create_task(_run_stream(api_key, secret_key, tickers))


async def stop_alpaca_stream() -> None:
    """Cancel the background stream task cleanly on server shutdown."""
    global _stream_task
    if _stream_task and not _stream_task.done():
        _stream_task.cancel()
        try:
            await _stream_task
        except asyncio.CancelledError:
            pass
    _stream_task = None
