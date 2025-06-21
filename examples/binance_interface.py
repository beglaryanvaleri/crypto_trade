"""
Example of basic Binance Futures operations.
"""
import asyncio
import time

from src.exchanges.binance import BinanceFuturesInterface
from src.utils.logger import setup_logger, get_logger
from src.config import Config

# Setup logging
setup_logger(log_level=Config.log_level)
logger = get_logger('example')


async def show_account_balance(interface):
    """Display account balance information."""
    logger.info("=== Account Balance ===")
    balance = interface.get_account_balance('USDT')
    if balance:
        logger.info(f"USDT Balance: {balance['balance']:.2f}")
        logger.info(f"Available: {balance['available_balance']:.2f}")
        return balance['balance']
    return 0


async def show_current_prices(interface, symbols):
    """Display current prices for given symbols."""
    logger.info("\n=== Current Prices ===")
    prices = {}
    for symbol in symbols:
        price = interface.get_price(symbol)
        if price:
            logger.info(f"{symbol}: ${price:,.2f}")
            prices[symbol] = price
    return prices


async def show_symbol_info(interface, symbol):
    """Display symbol information."""
    logger.info(f"\n=== Symbol Info for {symbol} ===")
    info = interface.get_symbol_info(symbol)
    if info:
        logger.info(f"Min Quantity: {info['min_qty']}")
        logger.info(f"Step Size: {info['qty_step']}")
        logger.info(f"Price Tick: {info['price_tick']}")
        logger.info(f"Min Notional: ${info['min_notional']}")
    return info


async def show_recent_klines(interface, symbol, interval='1h', limit=5):
    """Display recent candlestick data."""
    logger.info(f"\n=== Recent Klines ({symbol} {interval}) ===")
    klines = interface.get_klines(symbol, interval, limit=limit)
    for k in klines[-3:]:  # Last 3 candles
        logger.info(f"Time: {k['timestamp']}, O: ${k['open']:,.2f}, H: ${k['high']:,.2f}, "
                   f"L: ${k['low']:,.2f}, C: ${k['close']:,.2f}")
    return klines


async def show_open_positions(interface):
    """Display all open positions."""
    logger.info("\n=== Open Positions ===")
    positions = interface.get_all_positions()
    if positions:
        for pos in positions:
            logger.info(f"{pos['symbol']}: {pos['side']} {abs(pos['amount'])} @ ${pos['entry_price']:,.2f}, "
                       f"PnL: ${pos['unrealized_pnl']:.2f}")
    else:
        logger.info("No open positions")
    return positions


async def show_open_orders(interface):
    """Display all open orders."""
    logger.info("\n=== Open Orders ===")
    orders = interface.get_open_orders()
    if orders:
        for order in orders:
            logger.info(f"{order['symbol']}: {order['side']} {order['origQty']} @ ${order['price']}")
    else:
        logger.info("No open orders")
    return orders


async def calculate_position_size(interface, symbol, usdt_amount):
    """Calculate and display position sizing."""
    logger.info(f"\n=== Position Sizing for {symbol} ===")
    logger.info(f"USDT Amount: ${usdt_amount}")
    
    qty = interface.calculate_quantity_from_usdt(symbol, usdt_amount)
    if qty:
        price = interface.get_price(symbol)
        logger.info(f"Current Price: ${price:,.2f}")
        logger.info(f"Quantity: {qty}")
        logger.info(f"Actual Value: ${qty * price:.2f}")
        return qty
    else:
        logger.info("Unable to calculate (below minimum)")
        return None


async def demonstrate_limit_order(interface, symbol='BTCUSDT'):
    """Create, show, and cancel a limit order."""
    logger.info("\n=== Limit Order Example ===")
    
    # Get current price
    current_price = interface.get_price(symbol)
    if not current_price:
        logger.error("Could not get current price")
        return
    
    # Create a limit buy order 10% below current price
    order_price = round(current_price * 0.9, 2)
    order_quantity = interface.calculate_quantity_from_usdt(symbol, 250)  # 250 order
    
    if not order_quantity:
        logger.error("Could not calculate order quantity")
        return
    
    logger.info(f"Creating limit BUY order: {order_quantity} {symbol} @ ${order_price:,.2f}")
    
    # Create the limit order
    order = interface.create_limit_order(
        symbol=symbol,
        side='BUY',
        quantity=order_quantity,
        price=order_price
    )
    
    if order:
        order_id = order['orderId']
        logger.info(f"✓ Limit order created successfully! Order ID: {order_id}")
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Show open orders
        await show_open_orders(interface)
        
        # Cancel the order
        logger.info(f"\nCanceling order {order_id}...")
        cancel_result = interface.cancel_order(symbol, order_id)
        
        if cancel_result:
            logger.info("✓ Order canceled successfully!")
        
        # Verify cancellation
        await asyncio.sleep(1)
        await show_open_orders(interface)
    else:
        logger.error("Failed to create limit order")


async def demonstrate_market_order(interface, symbol='BTCUSDT', position_size_usdt=100):
    """Open a market position, show it, then close it."""
    logger.info("\n=== Market Order Example ===")
    logger.info(f"WARNING: This will open a REAL position with ${position_size_usdt}")
    
    # Check if we're on testnet
    if interface.testnet:
        logger.info("✓ Running on TESTNET - using test funds")
    else:
        logger.warning("⚠️  Running on PRODUCTION - using REAL funds!")
        logger.info("Waiting 3 seconds... Press Ctrl+C to cancel")
        await asyncio.sleep(3)
    
    # Calculate quantity
    quantity = interface.calculate_quantity_from_usdt(symbol, position_size_usdt)
    if not quantity:
        logger.error("Could not calculate quantity")
        return
    
    # Get current price for reference
    entry_price = interface.get_price(symbol)
    logger.info(f"\nOpening {symbol} position:")
    logger.info(f"  Side: BUY")
    logger.info(f"  Quantity: {quantity}")
    logger.info(f"  Current Price: ${entry_price:,.2f}")
    logger.info(f"  Est. Value: ${position_size_usdt}")
    
    # Create market order
    order = interface.create_market_order(
        symbol=symbol,
        side='BUY',
        quantity=quantity
    )
    
    if order:
        logger.info(f"✓ Market order executed!")
        logger.info(f"  Order ID: {order['orderId']}")
        logger.info(f"  Status: {order['status']}")
        
        # Wait for position to be registered
        await asyncio.sleep(2)
        
        # Show current positions
        positions = await show_open_positions(interface)
        
        # Find our position
        our_position = None
        for pos in positions:
            if pos['symbol'] == symbol:
                our_position = pos
                break
        
        if our_position:
            logger.info(f"\n=== Position Details ===")
            logger.info(f"Symbol: {our_position['symbol']}")
            logger.info(f"Side: {our_position['side']}")
            logger.info(f"Amount: {our_position['amount']}")
            logger.info(f"Entry Price: ${our_position['entry_price']:,.2f}")
            logger.info(f"Mark Price: ${our_position['mark_price']:,.2f}")
            logger.info(f"Unrealized PnL: ${our_position['unrealized_pnl']:.2f}")
            
            # Wait a bit to see price movement
            logger.info("\nWaiting 5 seconds to see price movement...")
            await asyncio.sleep(5)
            
            # Check position again
            updated_position = interface.get_position(symbol)
            if updated_position:
                logger.info(f"\n=== Updated Position ===")
                logger.info(f"Mark Price: ${updated_position['mark_price']:,.2f}")
                logger.info(f"Unrealized PnL: ${updated_position['unrealized_pnl']:.2f}")
            
            # Close the position
            logger.info(f"\n=== Closing Position ===")
            close_order = interface.close_position(symbol)
            
            if close_order:
                logger.info(f"✓ Position closed!")
                logger.info(f"  Close Order ID: {close_order['orderId']}")
                logger.info(f"  Status: {close_order['status']}")
                
                # Wait and verify position is closed
                await asyncio.sleep(2)
                await show_open_positions(interface)
            else:
                logger.error("Failed to close position")
        else:
            logger.warning("Could not find the opened position")
    else:
        logger.error("Failed to create market order")


async def main():
    """Main function that calls all examples."""
    logger.info("=== Binance Futures Interface Examples ===")
    
    # Initialize interface
    interface = BinanceFuturesInterface(
        api_key=Config.binance_api_key,
        api_secret=Config.binance_secret_key,
        testnet_api_key=Config.binance_testnet_api_key,
        testnet_api_secret=Config.binance_testnet_secret_key,
        mode=Config.binance_trading_mode,
        logger=logger
    )
    interface.refresh_symbols_info()
    
    # Basic information examples
    await show_account_balance(interface)
    await show_current_prices(interface, ['BTCUSDT', 'ETHUSDT'])
    await show_symbol_info(interface, 'BTCUSDT')
    await show_recent_klines(interface, 'BTCUSDT')
    
    # Show current state
    await show_open_positions(interface)
    await show_open_orders(interface)
    
    # Position sizing examples
    await calculate_position_size(interface, 'BTCUSDT', 200)
    await calculate_position_size(interface, 'ETHUSDT', 200)
    
    # Order examples
    await demonstrate_limit_order(interface, 'BTCUSDT')
    await demonstrate_market_order(interface, 'BTCUSDT', 200)
    
    logger.info("\n=== Examples Complete ===")

if __name__ == "__main__":
    asyncio.run(main())