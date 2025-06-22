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
        
        logger.info(f"Initialized copy trading strategy with {len(self.source_interfaces)} source accounts")
    
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
            mode=interface.testnet and "testnet" or "production",
            on_open=lambda: logger.info(f"Connected to {name} user data stream"),
            on_close=lambda: logger.info(f"Disconnected from {name} user data stream")
        )
        
        await ws_client.subscribe_user_data(listen_key)
        await ws_client.start()