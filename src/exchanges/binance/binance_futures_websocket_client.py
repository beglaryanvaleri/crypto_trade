import asyncio
import json
import time
from typing import Dict, List
import websockets

from utils.logger import get_logger
from config import Config


class BinanceFuturesWebSocketClient:
    def __init__(self, api_key=None, api_secret=None, testnet_api_key=None, testnet_api_secret=None, mode=None,
                 on_message=None, on_error=None, on_close=None, on_open=None, logger=None):
        self.logger = logger or get_logger(__name__)

        if mode == "testnet":
            self.api_key = testnet_api_key
            self.api_secret = testnet_api_secret
            self.testnet = True
            self.base_url = Config.binance_futures_testnet_base_url
            self.ws_url = Config.binance_futures_testnet_ws_url
            self.logger.info("Using Binance TESTNET")
        else:
            self.api_key = api_key
            self.api_secret = api_secret
            self.testnet = False
            self.base_url = Config.binance_futures_base_url
            self.ws_url = Config.binance_futures_ws_url
            self.logger.info("Using Binance LIVE")

        # Connection management
        self.ws = None
        self._running = False
        self._reconnect_count = 0
        self._subscribed_streams = []
        self._listen_key = None
        self._user_data_stream = False
        
        # Reconnection settings
        self.reconnect_interval = 5  # Base reconnect interval in seconds
        self.max_reconnect_interval = 300  # Max 5 minutes
        self.max_reconnect_attempts = None  # None = unlimited
        
        
        # Event handlers
        self.on_message = on_message or self._default_on_message
        self.on_error = on_error or self._default_on_error
        self.on_close = on_close or self._default_on_close
        self.on_open = on_open or self._default_on_open
        
    def _default_on_message(self, message: Dict):
        """Default message handler - shows message types and logs full message."""
        # Handle stream messages (market data)
        if 'stream' in message and 'data' in message:
            stream = message['stream']
            data = message['data']
            
            if '@aggTrade' in stream:
                self.logger.info(f"Trade message: {message}")
            elif '@markPrice' in stream:
                self.logger.info(f"Mark price message: {message}")
            elif '@miniTicker' in stream:
                self.logger.info(f"Ticker message: {message}")
            elif '@depth' in stream:
                self.logger.info(f"Orderbook message: {message}")
            elif '@kline' in stream:
                self.logger.info(f"Kline message: {message}")
            else:
                self.logger.info(f"Market data message: {message}")
        
        # Handle user data messages
        elif 'e' in message:
            event_type = message['e']
            
            if event_type == 'ORDER_TRADE_UPDATE':
                self.logger.info(f"Order update message: {message}")
            elif event_type == 'ACCOUNT_UPDATE':
                self.logger.info(f"Account update message: {message}")
            elif event_type == 'listenKeyExpired':
                self.logger.info(f"Listen key expired message: {message}")
            elif event_type == 'TRADE_LITE':
                self.logger.info(f"Trade lite message: {message}")
            else:
                self.logger.info(f"User data message ({event_type}): {message}")
        
        # Handle other messages
        else:
            self.logger.info(f"Unknown message type: {message}")
        
    def _default_on_error(self, error: Exception):
        """Default error handler - logs the error."""
        self.logger.error(f"WebSocket error: {error}")
        
    def _default_on_close(self):
        """Default close handler - logs the close event."""
        self.logger.info("WebSocket connection closed")
        
    def _default_on_open(self):
        """Default open handler - logs the open event."""
        self.logger.info("WebSocket connection opened")
        
    def subscribe(self, streams: List[str]):
        """
        Subscribe to WebSocket streams.
        
        Args:
            streams: List of stream names to subscribe to
            
        Example streams:
            - 'btcusdt@aggTrade' - Aggregate trades
            - 'btcusdt@markPrice' - Mark price
            - 'btcusdt@depth' - Order book
            - 'btcusdt@kline_1m' - 1 minute klines
            
        Note: If already connected, subscription happens immediately.
        If not connected, streams will be subscribed when connection starts.
        """
        self._subscribed_streams.extend(streams)
        self._subscribed_streams = list(set(self._subscribed_streams))  # Remove duplicates
        self.logger.info(f"Added streams to subscription list: {streams}")
            
    def unsubscribe(self, streams: List[str]):
        """Unsubscribe from WebSocket streams."""
        for stream in streams:
            if stream in self._subscribed_streams:
                self._subscribed_streams.remove(stream)
        self.logger.info(f"Removed streams from subscription list: {streams}")
        
    async def subscribe_now(self, streams: List[str]):
        """Subscribe to streams immediately (async version)."""
        self.subscribe(streams)  # Add to list
        if self.is_connected:
            await self._send_subscribe_message(streams)
            
    async def unsubscribe_now(self, streams: List[str]):
        """Unsubscribe from streams immediately (async version)."""
        self.unsubscribe(streams)  # Remove from list
        if self.is_connected:
            await self._send_unsubscribe_message(streams)
            
    async def _send_subscribe_message(self, streams: List[str]):
        """Send subscribe message to WebSocket."""
        if not self.ws or self.ws.closed:
            return
            
        message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000)
        }
        
        try:
            await self.ws.send(json.dumps(message))
            self.logger.info(f"Subscribed to streams: {streams}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe: {e}")
            
    async def _send_unsubscribe_message(self, streams: List[str]):
        """Send unsubscribe message to WebSocket."""
        if not self.ws or self.ws.closed:
            return
            
        message = {
            "method": "UNSUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000)
        }
        
        try:
            await self.ws.send(json.dumps(message))
            self.logger.info(f"Unsubscribed from streams: {streams}")
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe: {e}")
            
                
    async def _handle_messages(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.ws:
                if not self._running:
                    break
                    
                try:
                    # Parse message
                    if isinstance(message, str):
                        data = json.loads(message)
                    else:
                        data = message
                        
                    # Skip subscription confirmations
                    if isinstance(data, dict) and 'result' in data and data['result'] is None:
                        continue
                        
                    # Call message handler
                    if asyncio.iscoroutinefunction(self.on_message):
                        await self.on_message(data)
                    else:
                        self.on_message(data)
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse message: {e}, Raw: {message}")
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
                    if asyncio.iscoroutinefunction(self.on_error):
                        await self.on_error(e)
                    else:
                        self.on_error(e)
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")
            if asyncio.iscoroutinefunction(self.on_error):
                await self.on_error(e)
            else:
                self.on_error(e)
                
    async def _connect(self):
        """Establish WebSocket connection."""
        # Check if this is a user data stream
        if self._user_data_stream and self._listen_key:
            url = f"{self.ws_url}/ws/{self._listen_key}"
        elif self._subscribed_streams:
            # Build URL with streams
            streams_param = "/".join(self._subscribed_streams)
            url = f"{self.ws_url}/stream?streams={streams_param}"
        else:
            # Combined streams endpoint
            url = f"{self.ws_url}/ws"
            
        self.logger.info(f"Connecting to {url}")
        
        try:
            self.ws = await websockets.connect(
                url,
                ping_interval=None,  # Binance handles pings
                close_timeout=10
            )
            
            self._reconnect_count = 0
            
            # Call open handler
            if asyncio.iscoroutinefunction(self.on_open):
                await self.on_open()
            else:
                self.on_open()
                
            # Subscribe to streams if using /ws endpoint
            if not self._subscribed_streams:
                pass
            elif url.endswith('/ws') and self._subscribed_streams:
                await self._send_subscribe_message(self._subscribed_streams)
                
            # Handle messages
            await self._handle_messages()
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            if asyncio.iscoroutinefunction(self.on_error):
                await self.on_error(e)
            else:
                self.on_error(e)
            raise
            
    async def _reconnect(self):
        """Reconnect with exponential backoff."""
        while self._running:
            self._reconnect_count += 1
            
            # Check max attempts
            if self.max_reconnect_attempts and self._reconnect_count > self.max_reconnect_attempts:
                self.logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
                self._running = False
                break
                
            # Calculate backoff time
            backoff = min(
                self.reconnect_interval * (2 ** (self._reconnect_count - 1)),
                self.max_reconnect_interval
            )
            
            self.logger.info(f"Reconnecting in {backoff}s (attempt {self._reconnect_count})")
            await asyncio.sleep(backoff)
            
            try:
                await self._connect()
                break  # Successful connection
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")
                continue
                
    async def start(self):
        """Start the WebSocket connection."""
        if self._running:
            self.logger.warning("WebSocket already running")
            return
            
        self._running = True
        self.logger.info("Starting WebSocket client")
        
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                self.logger.error(f"Connection failed: {e}")
                
            # Call close handler
            if asyncio.iscoroutinefunction(self.on_close):
                await self.on_close()
            else:
                self.on_close()
                
            # Clean up tasks - no ping task needed for Binance
                
            # Reconnect if still running
            if self._running:
                await self._reconnect()
                
    async def stop(self):
        """Stop the WebSocket connection."""
        self.logger.info("Stopping WebSocket client")
        self._running = False

        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            
    async def send(self, message: Dict):
        if not self.is_connected:
            raise RuntimeError("WebSocket is not connected")
            
        try:
            await self.ws.send(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
            
    @property
    def is_connected(self) -> bool:
        try:
            return self.ws is not None and self.ws.open
        except:
            return False

    async def subscribe_user_data(self, listen_key: str):
        if not listen_key:
            raise ValueError("Listen key is required for user data stream")

        # For user data, we need to connect directly to the listen key URL
        # Store the listen key for reconnection
        self._listen_key = listen_key
        self._user_data_stream = True
        
        # If already connected, we need to reconnect with the new URL
        if self.is_connected:
            await self.stop()
            await self.start()
        else:
            self.logger.info(f"User data stream configured with listen key: {listen_key[:8]}...")