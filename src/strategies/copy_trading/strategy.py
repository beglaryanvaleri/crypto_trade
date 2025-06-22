import asyncio
from src.exchanges.binance import BinanceFuturesInterface
from src.exchanges.binance.binance_futures_websocket_client import BinanceFuturesWebSocketClient
from src.strategies.copy_trading.config import Config
from src.utils.logger import get_logger

logger = get_logger('copy_trading.strategy')


class CopyTradingStrategy:
    
    def __init__(self):
        yaml = Config.yaml
        
        main_account = yaml['main_account']
        self.main_interface = BinanceFuturesInterface(
            api_key=main_account['api_key'],
            api_secret=main_account['api_secret'],
            testnet_api_key=main_account['testnet_api_key'],
            testnet_api_secret=main_account['testnet_api_secret'],
            mode=main_account['mode']
        )
        
        self.source_interfaces = {}
        self.source_configs = {}
        self.executed_orders = {}  # Track executed orders by source
        
        for source in yaml['source_accounts']:
            if not source.get('enabled', True):
                continue
                
            interface = BinanceFuturesInterface(
                api_key=source['api_key'],
                api_secret=source['api_secret'],
                testnet_api_key=source['testnet_api_key'],
                testnet_api_secret=source['testnet_api_secret'],
                mode=source['mode']
            )
            self.source_interfaces[source['name']] = interface
            self.source_configs[source['name']] = source
            self.executed_orders[source['name']] = []
        
        logger.info(f"Initialized copy trading strategy with {len(self.source_interfaces)} source accounts")
    
    def _create_message_handler(self, source_name):
        def on_message(message):
            if 'e' in message:
                event_type = message['e']
                
                if event_type == 'ORDER_TRADE_UPDATE':
                    # Order execution details
                    order = message['o']
                    symbol = order['s']
                    side = order['S']
                    order_status = order['X']
                    executed_qty = float(order['z'])  # Cumulative filled quantity
                    executed_price = float(order['ap'])  # Average price
                    order_id = order['i']
                    client_order_id = order['c']
                    
                    if order_status == 'FILLED' and executed_qty > 0:
                        logger.info(f"[{source_name}] EXECUTION: {symbol} {side} {executed_qty} @ ${executed_price:,.2f}")
                        
                        # Store execution for future copying
                        execution = {
                            'timestamp': message['E'],
                            'symbol': symbol,
                            'side': side,
                            'quantity': executed_qty,
                            'price': executed_price,
                            'order_id': order_id,
                            'client_order_id': client_order_id
                        }
                        self.executed_orders[source_name].append(execution)
                        asyncio.create_task(self._copy_trade(source_name, execution))
                        
                    elif order_status in ['PARTIALLY_FILLED', 'NEW', 'CANCELED', 'EXPIRED']:
                        logger.info(f"[{source_name}] Order update: {symbol} {side} status={order_status}")
                else:
                    logger.info(f"[{source_name}] Received {event_type} message")
            else:
                logger.info(f"[{source_name}] Received message without event type")
        
        return on_message
    
    async def _copy_trade(self, source_name, execution):
        try:
            source_config = self.source_configs[source_name]
            symbol = execution['symbol']
            side = execution['side']
            original_qty = execution['quantity']
            price = execution['price']
            
            # Apply coefficient
            coefficient = source_config.get('coefficient', 1.0)
            calculated_qty = original_qty * coefficient
            
            # Round quantity to correct precision
            rounded_qty = self.main_interface.round_quantity_to_lot(symbol, calculated_qty)
            
            # Apply reverse trading if enabled
            if source_config.get('reverse_trades', False):
                side = 'SELL' if side == 'BUY' else 'BUY'
            
            logger.info(f"[COPY] {source_name} -> MAIN: {symbol} {side} {original_qty} * {coefficient} = {calculated_qty} -> {rounded_qty}")
            
            # Execute market order on main account
            result = self.main_interface.create_market_order(symbol, side, rounded_qty)
            
            if result:
                logger.info(f"[COPY] SUCCESS: {result}")
            else:
                logger.error(f"[COPY] FAILED: Could not execute {symbol} {side} {rounded_qty}")
                
        except Exception as e:
            logger.error(f"[COPY] ERROR: {e}")

    async def run(self):
        logger.info("Starting copy trading strategy...")
        
        try:
            tasks = []
            for name, interface in self.source_interfaces.items():
                task = asyncio.create_task(self._listen_source_account(name, interface))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
                
        except KeyboardInterrupt:
            logger.info("Copy trading strategy stopped by user")
        except Exception as e:
            logger.error(f"Error in copy trading strategy: {e}")
    
    async def _listen_source_account(self, name, interface):
        logger.info(f"Starting WebSocket listener for {name}")
        
        listen_key = interface.get_listen_key()
        if not listen_key:
            logger.error(f"Failed to get listen key for {name}")
            return
        
        logger.info(f"Got listen key for {name}: {listen_key[:8]}...")
        
        ws_client = BinanceFuturesWebSocketClient(
            mode=self.source_configs[name]['mode'],
            on_message=self._create_message_handler(name),
            on_open=lambda: logger.info(f"Connected to {name} user data stream"),
            on_close=lambda: logger.info(f"Disconnected from {name} user data stream")
        )
        
        await ws_client.subscribe_user_data(listen_key)
        await ws_client.start()