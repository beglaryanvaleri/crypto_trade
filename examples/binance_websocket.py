"""
Simple Binance WebSocket examples.
"""
import asyncio
from src.exchanges.binance.binance_futures_websocket_client import BinanceFuturesWebSocketClient
from src.utils.logger import setup_logger, get_logger
from src.config import Config

setup_logger(log_level=Config.log_level)
logger = get_logger('websocket_example')


async def public_streams_example():
    """Example subscribing to public market data streams."""
    logger.info("=== Public Streams Example ===")
    
    # Create WebSocket client
    ws_client = BinanceFuturesWebSocketClient(
        mode=Config.binance_trading_mode,
        on_open=lambda: logger.info("Connected to public streams"),
        on_close=lambda: logger.info("Disconnected from public streams")
    )
    
    # Subscribe to public streams
    streams = [
        'btcusdt@aggTrade',      # BTC trades
        'btcusdt@markPrice@1s',  # BTC mark price
        'btcusdt@miniTicker',    # BTC ticker
    ]
    
    ws_client.subscribe(streams)
    
    # Start and run for 10 seconds
    task = asyncio.create_task(ws_client.start())
    await asyncio.sleep(10)
    
    await ws_client.stop()
    await task


async def trading_with_websocket():
    """Example executing trades and monitoring via WebSocket."""
    logger.info("=== Trading with WebSocket Example ===")
    
    # Import interface for trading
    from src.exchanges.binance import BinanceFuturesInterface
    
    # Create trading interface
    interface = BinanceFuturesInterface(
        api_key=Config.binance_api_key,
        api_secret=Config.binance_secret_key,
        testnet_api_key=Config.binance_testnet_api_key,
        testnet_api_secret=Config.binance_testnet_secret_key,
        mode=Config.binance_trading_mode
    )
    
    # Get listen key for user data stream
    listen_key = interface.get_listen_key()
    if not listen_key:
        logger.error("Failed to get listen key - check API credentials")
        return
    
    logger.info(f"Got listen key: {listen_key[:8]}...")
    
    # Create WebSocket for user data
    ws_client = BinanceFuturesWebSocketClient(
        mode=Config.binance_trading_mode,
        on_open=lambda: logger.info("Connected to user data stream"),
        on_close=lambda: logger.info("Disconnected from user data stream")
    )
    
    # Subscribe to user data stream
    await ws_client.subscribe_user_data(listen_key)
    
    # Start WebSocket connection
    task = asyncio.create_task(ws_client.start())
    await asyncio.sleep(2)  # Wait for connection
    
    # Execute some trades
    logger.info("Executing test trades...")
    
    # Get current BTC price
    symbol = "BTCUSDT"
    cur_price = interface.get_price(symbol)
    if cur_price:
        logger.info(f"Current {symbol} price: ${cur_price:,.2f}")
        
        # 1. Place limit order below market
        limit_price = round(cur_price * 0.95, 2)
        limit_price = interface.round_price_to_tick(symbol, limit_price)
        quantity = interface.calculate_quantity_from_usdt(symbol, 1000)
        
        if quantity:
            logger.info(f"Placing limit buy order. quantity: {quantity} @ ${limit_price}")
            order1 = interface.create_limit_order(symbol, 'BUY', quantity, limit_price)
            if order1:
                await asyncio.sleep(3)  # Wait for WebSocket message
                
                # Cancel the order
                logger.info(f"Canceling order {order1['orderId']}")
                interface.cancel_order(symbol, order1['orderId'])
                await asyncio.sleep(3)  # Wait for WebSocket message
    
    # Keep listening for a few more seconds
    await asyncio.sleep(10)
    
    # Stop WebSocket
    await ws_client.stop()
    await task


async def main():
    """Run WebSocket examples."""
    try:
        # Run public streams example
        await public_streams_example()
        await asyncio.sleep(2)
        
        # Run trading example
        await trading_with_websocket()
        
    except KeyboardInterrupt:
        logger.info("Examples interrupted by user")
    except Exception as e:
        logger.error(f"Example error: {e}")


if __name__ == "__main__":
    asyncio.run(main())