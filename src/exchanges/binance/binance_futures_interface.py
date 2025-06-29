"""
Binance Futures client implementation.
"""
from typing import Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from binance import Client
import requests
import time

from utils.logger import get_logger
from config import Config

class BinanceFuturesInterface:
    """Interface for interacting with Binance Futures API."""
    
    def __init__(self, api_key=None, api_secret=None, testnet_api_key=None, testnet_api_secret=None, mode=None,
                 logger=None):
        """
        Initialize Binance Futures client.
        """

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
            self.logger.info("Using Binance PRODUCTION")

        self._client = Client(self.api_key, self.api_secret, testnet=self.testnet)
        self._symbols_info = {}

    def refresh_symbols_info(self) -> None:
        """Refresh and cache symbol information."""
        try:
            exchange_info = self._client.futures_exchange_info()
            self._symbols_info = {}
            
            for symbol_data in exchange_info['symbols']:
                filters = {f['filterType']: f for f in symbol_data['filters']}
                self._symbols_info[symbol_data['symbol']] = {
                    "min_qty": float(filters['LOT_SIZE']['minQty']),
                    "qty_step": float(filters['LOT_SIZE']['stepSize']),
                    "qty_precision": symbol_data['quantityPrecision'],
                    "price_precision": symbol_data['pricePrecision'],
                    "price_tick": float(filters['PRICE_FILTER']['tickSize']),
                    "min_notional": float(filters['MIN_NOTIONAL']['notional']) if 'MIN_NOTIONAL' in filters else 0
                }
            self.logger.info(f"Loaded info for {len(self._symbols_info)} symbols")
        except Exception as e:
            self.logger.error(f"Failed to refresh symbols info: {e}")
            
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get cached symbol information."""
        return self._symbols_info.get(symbol)
    
    def get_active_futures_symbols(self) -> List[str]:
        """Get list of active perpetual futures symbols."""
        try:
            exchange_info = self._client.futures_exchange_info()
            symbols = []
            
            for symbol_info in exchange_info['symbols']:
                if symbol_info['status'] == 'TRADING' and symbol_info['contractType'] == 'PERPETUAL':
                    symbols.append(symbol_info['symbol'].lower())
            
            self.logger.info(f"Found {len(symbols)} active perpetual futures symbols")
            return symbols
            
        except Exception as e:
            self.logger.error(f"Failed to get active symbols: {e}")
            return []
        
    def get_account_balance(self, asset: str = 'USDT') -> Optional[Dict[str, float]]:
        """
        Get account balance for specific asset.
        
        Returns:
            Dict with 'asset', 'balance', 'available_balance' or None
        """
        try:
            balances = self._client.futures_account_balance()
            for balance in balances:
                if balance['asset'] == asset:
                    return {
                        'asset': balance['asset'],
                        'balance': float(balance['balance']),
                        'available_balance': float(balance['availableBalance'])
                    }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get account balance: {e}")
            return None
            
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        try:
            ticker = self._client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            self.logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict]:
        """
        Get candlestick data.
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of klines to retrieve
            
        Returns:
            List of kline dicts with OHLCV data
        """
        try:
            klines = self._client.futures_klines(symbol=symbol, interval=interval, limit=limit)
            return [
                {
                    "timestamp": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "quote_volume": float(k[7]),
                    "trades": k[8]
                }
                for k in klines
            ]
        except Exception as e:
            self.logger.error(f"Failed to get klines for {symbol}: {e}")
            return []
    
    def get_historical_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> List[Dict]:
        """
        Get historical candlestick data for a specific time range.
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            List of kline dicts with OHLCV data
        """
        try:
            all_klines = []
            current_start = start_time
            limit = 1500  # Binance max limit
            
            while current_start < end_time:
                # Get batch of klines
                klines = self._client.futures_klines(
                    symbol=symbol,
                    interval=interval,
                    startTime=current_start,
                    endTime=end_time,
                    limit=limit
                )
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                
                # Update start time for next batch
                # Set to last candle timestamp + interval
                last_timestamp = klines[-1][0]
                
                # Calculate interval in milliseconds
                interval_ms = {
                    '1m': 60000,
                    '3m': 180000,
                    '5m': 300000,
                    '15m': 900000,
                    '30m': 1800000,
                    '1h': 3600000,
                    '2h': 7200000,
                    '4h': 14400000,
                    '6h': 21600000,
                    '8h': 28800000,
                    '12h': 43200000,
                    '1d': 86400000,
                    '3d': 259200000,
                    '1w': 604800000,
                    '1M': 2592000000
                }.get(interval, 60000)
                
                current_start = last_timestamp + interval_ms
                
                # If we got less than limit, we're done
                if len(klines) < limit:
                    break
                
                # Small delay to avoid rate limits
                time.sleep(0.1)
            
            # Convert to our format
            return [
                {
                    "timestamp": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "quote_volume": float(k[7]),
                    "trades": k[8]
                }
                for k in all_klines
            ]
        except Exception as e:
            self.logger.error(f"Failed to get historical klines for {symbol}: {e}")
            return []
            
    def create_market_order(self, symbol: str, side: str, quantity: float, 
                          reduce_only: bool = False) -> Optional[Dict]:
        """
        Create a market order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            reduce_only: Whether to only reduce position
            
        Returns:
            Order response or None
        """
        try:
            order = self._client.futures_create_order(
                symbol=symbol,
                side=side.upper(),
                type='MARKET',
                quantity=quantity,
                reduceOnly=reduce_only
            )
            self.logger.info(f"Market order created: {symbol} {side} {quantity}")
            return order
        except Exception as e:
            self.logger.error(f"Failed to create market order: {e}")
            return None
            
    def create_limit_order(self, symbol: str, side: str, quantity: float, 
                         price: float, reduce_only: bool = False,
                         time_in_force: str = 'GTC', post_only: bool = False) -> Optional[Dict]:
        """
        Create a limit order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL' 
            quantity: Order quantity
            price: Order price
            reduce_only: Whether to only reduce position
            time_in_force: Time in force (GTC, IOC, FOK)
            post_only: Maker-only order
            
        Returns:
            Order response or None
        """
        try:
            params = {
                'symbol': symbol,
                'side': side.upper(),
                'type': 'LIMIT',
                'quantity': quantity,
                'price': price,
                'timeInForce': time_in_force,
                'reduceOnly': reduce_only
            }
            
            if post_only and time_in_force == 'GTC':
                params['postOnly'] = True
                
            order = self._client.futures_create_order(**params)
            self.logger.info(f"Limit order created: {symbol} {side} {quantity}@{price}")
            return order
        except Exception as e:
            self.logger.error(f"Failed to create limit order: {e}")
            return None
            
    def cancel_order(self, symbol: str, order_id: int) -> Optional[Dict]:
        """Cancel an order."""
        try:
            result = self._client.futures_cancel_order(symbol=symbol, orderId=order_id)
            self.logger.info(f"Order cancelled: {symbol} {order_id}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            return None
            
    def get_order(self, symbol: str, order_id: int) -> Optional[Dict]:
        """Get order details."""
        try:
            return self._client.futures_get_order(symbol=symbol, orderId=order_id)
        except Exception as e:
            self.logger.error(f"Failed to get order {order_id}: {e}")
            return None
            
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders."""
        try:
            return self._client.futures_get_open_orders(symbol=symbol)
        except Exception as e:
            self.logger.error(f"Failed to get open orders: {e}")
            return []
            
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position information for symbol.
        
        Returns:
            Position dict with amount, entry price, unrealized PnL, etc.
        """
        try:
            positions = self._client.futures_position_information(symbol=symbol)
            for pos in positions:
                amt = float(pos['positionAmt'])
                if amt != 0:
                    return {
                        'symbol': pos['symbol'],
                        'amount': amt,
                        'entry_price': float(pos['entryPrice']),
                        'mark_price': float(pos['markPrice']),
                        'unrealized_pnl': float(pos['unRealizedProfit']),
                        'liquidation_price': float(pos['liquidationPrice']) if pos['liquidationPrice'] else None,
                        'side': 'LONG' if amt > 0 else 'SHORT'
                    }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get position for {symbol}: {e}")
            return None
            
    def get_all_positions(self) -> List[Dict]:
        """Get all open positions."""
        try:
            positions = self._client.futures_position_information()
            open_positions = []
            
            for pos in positions:
                amt = float(pos['positionAmt'])
                if amt != 0:
                    open_positions.append({
                        'symbol': pos['symbol'],
                        'amount': amt,
                        'entry_price': float(pos['entryPrice']),
                        'mark_price': float(pos['markPrice']),
                        'unrealized_pnl': float(pos['unRealizedProfit']),
                        'side': 'LONG' if amt > 0 else 'SHORT'
                    })
                    
            return open_positions
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return []
            
    def close_position(self, symbol: str) -> Optional[Dict]:
        """Close position for symbol using market order."""
        position = self.get_position(symbol)
        if not position:
            self.logger.info(f"No position to close for {symbol}")
            return None
            
        quantity = abs(position['amount'])
        side = 'SELL' if position['side'] == 'LONG' else 'BUY'
        
        return self.create_market_order(symbol, side, quantity, reduce_only=True)
        
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for symbol."""
        try:
            self._client.futures_change_leverage(symbol=symbol, leverage=leverage)
            self.logger.info(f"Leverage set to {leverage}x for {symbol}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to set leverage: {e}")
            return False
            
    def _get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information including tick size."""
        try:
            if not hasattr(self, '_symbol_info_cache'):
                self._symbol_info_cache = {}
                
            if symbol not in self._symbol_info_cache:
                exchange_info = self._client.futures_exchange_info()
                for s in exchange_info['symbols']:
                    if s['symbol'] == symbol:
                        self._symbol_info_cache[symbol] = s
                        break
                        
            return self._symbol_info_cache.get(symbol)
        except Exception as e:
            self.logger.error(f"Failed to get symbol info for {symbol}: {e}")
            return None

    def round_price_to_tick(self, symbol: str, price: float) -> float:
        """Round price to correct tick size for symbol."""
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            # Fallback for common symbols
            if 'USDT' in symbol:
                return float(Decimal(str(price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            return price

        # Find tick size from price filter
        for f in symbol_info['filters']:
            if f['filterType'] == 'PRICE_FILTER':
                tick_size = Decimal(str(f['tickSize']))
                rounded = (Decimal(str(price)) / tick_size).quantize(0, rounding=ROUND_HALF_UP) * tick_size
                return float(rounded)

        return price

    def round_quantity_to_lot(self, symbol: str, quantity: float) -> float:
        """Round quantity to correct lot size for symbol."""
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            # Fallback for common symbols
            if 'USDT' in symbol:
                return float(Decimal(str(quantity)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
            return quantity

        # Find lot size from quantity filter
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step_size = Decimal(str(f['stepSize']))
                rounded = (Decimal(str(quantity)) / step_size).quantize(0, rounding=ROUND_HALF_UP) * step_size
                return float(rounded)

        return quantity

    def get_listen_key(self) -> Optional[str]:
        """Get listen key for websocket user data stream."""
        try:
            response = requests.post(
                f"{self.base_url}/fapi/v1/listenKey",
                headers={"X-MBX-APIKEY": self.api_key}
            )
            if response.status_code == 200:
                return response.json()["listenKey"]
            else:
                self.logger.error(f"Failed to get listen key: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting listen key: {e}")
            return None

    def calculate_quantity_from_usdt(self, symbol: str, usdt_amount: float) -> Optional[float]:
        """
        Calculate quantity of tokens for given USDT amount.
        
        Args:
            symbol: Trading pair (must be USDT pair)
            usdt_amount: Amount in USDT to convert
            
        Returns:
            Quantity of tokens adjusted to symbol's precision, or None if error
        """
        try:
            # Verify it's a USDT pair
            if not symbol.endswith('USDT'):
                self.logger.error(f"{symbol} is not a USDT pair")
                return None
                
            # Get current price
            price = self.get_price(symbol)
            if not price:
                return None
                
            # Get symbol info for precision
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                # Refresh symbols info and try again
                self.refresh_symbols_info()
                symbol_info = self.get_symbol_info(symbol)
                if not symbol_info:
                    self.logger.error(f"Symbol info not found for {symbol}")
                    return None
            
            # Calculate raw quantity
            raw_quantity = usdt_amount / price
            
            # Round to symbol's step size
            step_size = symbol_info['qty_step']
            qty_precision = symbol_info['qty_precision']
            
            # Round down to nearest step size
            quantity = raw_quantity - (raw_quantity % step_size)
            
            # Round to correct decimal places
            quantity = round(quantity, qty_precision)
            
            # Check minimum quantity
            if quantity < symbol_info['min_qty']:
                self.logger.warning(f"Calculated quantity {quantity} is below minimum {symbol_info['min_qty']} for {symbol}")
                return None
                
            # Check minimum notional value
            notional = quantity * price
            if notional < symbol_info['min_notional']:
                self.logger.warning(f"Notional value ${notional:.2f} is below minimum ${symbol_info['min_notional']:.2f} for {symbol}")
                return None
                
            self.logger.info(f"{symbol}: ${usdt_amount:.2f} = {quantity} tokens at ${price:.2f}")
            return quantity
            
        except Exception as e:
            self.logger.error(f"Failed to calculate quantity for {symbol}: {e}")
            return None