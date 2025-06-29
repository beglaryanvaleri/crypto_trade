"""
Monitor liquidation order streams for all active futures symbols.
"""
import asyncio
import argparse
import json
import os
from datetime import datetime
from exchanges.binance import BinanceFuturesInterface
from exchanges.binance.binance_futures_websocket_client import BinanceFuturesWebSocketClient
from utils.logger import setup_logger, get_logger
from config import Config

setup_logger(log_level=Config.log_level)
logger = get_logger('liquidation_monitor')


async def monitor_liquidations(trade_mode: str, save_data: bool):
    """Monitor liquidation streams for all active futures symbols."""
    logger.info("=== Liquidation Monitor ===")
    logger.info(f"Trade mode: {trade_mode}")
    logger.info(f"Save data: {save_data}")
    
    # Setup data saving if enabled
    data_file = None
    if save_data:
        data_dir = "data/liquidations"
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_file = f"{data_dir}/liquidations_{trade_mode}_{timestamp}.jsonl"
        logger.info(f"Saving liquidation data to: {data_file}")
    
    # Create interface to get all symbols
    interface = BinanceFuturesInterface(
        api_key=Config.binance_api_key,
        api_secret=Config.binance_secret_key,
        testnet_api_key=Config.binance_testnet_api_key,
        testnet_api_secret=Config.binance_testnet_secret_key,
        mode=trade_mode
    )
    
    # Get all active futures symbols
    symbols = interface.get_active_futures_symbols()
    if not symbols:
        raise ValueError("No active futures symbols found. Check your network connection.")
    
    # Create liquidation streams for all symbols
    streams = [f'{symbol}@forceOrder' for symbol in symbols]
    
    logger.info(f"Monitoring {len(symbols)} symbols for liquidations")
    
    # Counter for liquidations
    liquidation_count = {'total': 0, 'by_symbol': {}}
    
    # Custom message handler for liquidations
    def on_liquidation_message(message):
        # Handle stream messages
        if 'stream' in message and 'data' in message:
            stream = message['stream']
            data = message['data']
            
            if '@forceOrder' in stream and 'o' in data:
                order = data['o']
                symbol = order['s']
                side = order['S']
                quantity = order['q']
                price = order['p']
                avg_price = order['ap']
                timestamp = data['E']
                
                # Calculate USD amount (notional value)
                usdt_amount = float(quantity) * float(avg_price)
                
                # Update counters
                liquidation_count['total'] += 1
                if symbol not in liquidation_count['by_symbol']:
                    liquidation_count['by_symbol'][symbol] = 0
                liquidation_count['by_symbol'][symbol] += 1
                
                # Create liquidation record
                liquidation_record = {
                    'timestamp': timestamp,
                    'datetime': datetime.fromtimestamp(timestamp / 1000).isoformat(),
                    'symbol': symbol,
                    'side': side,
                    'quantity': float(quantity),
                    'price': float(price),
                    'avg_price': float(avg_price),
                    'usdt_amount': usdt_amount,
                    'order_status': order['X'],
                    'order_type': order['o'],
                    'time_in_force': order['f']
                }
                
                # Save to file if enabled
                if save_data and data_file:
                    try:
                        with open(data_file, 'a') as f:
                            f.write(json.dumps(liquidation_record) + '\n')
                    except Exception as e:
                        logger.error(f"Failed to save liquidation data: {e}")
                
                logger.warning(f"🔴 LIQUIDATION #{liquidation_count['total']}: {symbol} {side} {quantity} @ ${price} (avg: ${avg_price}) = ${usdt_amount:,.2f}")
                # logger.info(f"Liquidation details: Symbol={symbol}, Side={side}, Qty={quantity}, Price=${price}, AvgPrice=${avg_price}, USDAmount=${usdt_amount:,.2f}")
    
    # Create WebSocket client
    ws_client = BinanceFuturesWebSocketClient(
        mode=trade_mode,
        on_message=on_liquidation_message,
        on_open=lambda: logger.info("Connected to liquidation streams"),
        on_close=lambda: logger.info("Disconnected from liquidation streams")
    )
    
    # Subscribe to liquidation streams
    ws_client.subscribe(streams)
    
    # Run indefinitely
    logger.info("Starting liquidation monitor... Press Ctrl+C to stop")
    await ws_client.start()


async def main():
    """Run liquidation monitor."""
    parser = argparse.ArgumentParser(description='Monitor Binance Futures liquidation orders')
    parser.add_argument('--trade-mode', choices=['testnet', 'live'], default='live',
                        help='Trading mode: testnet or live (default: testnet)')
    parser.add_argument('--save-data', action='store_true',
                        help='Save liquidation data to JSON lines file')
    
    args = parser.parse_args()
    
    try:
        await monitor_liquidations(args.trade_mode, args.save_data)
    except KeyboardInterrupt:
        logger.info("Liquidation monitor stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())