"""
Global configuration module.
Loads environment variables from root .env file regardless of where it's imported from.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from src.utils.logger import get_logger

logger = get_logger('config')

class Config:
    """Global configuration class with environment variables."""
    
    # Find project root directory (where .env should be)
    _root_dir = Path(__file__).parent.parent  # Go up from src/ to project root
    _env_file = _root_dir / '.env'
    
    # Load environment variables from root .env file
    if _env_file.exists():
        load_dotenv(_env_file)
        logger.info(f"Loaded environment from {_env_file}")
    else:
        logger.warning(f".env file not found at {_env_file}")

    binance_api_key = os.getenv('BINANCE_API_KEY')
    binance_secret_key = os.getenv('BINANCE_API_SECRET')
    binance_testnet_api_key = os.getenv('BINANCE_TESTNET_API_KEY')
    binance_testnet_secret_key = os.getenv('BINANCE_TESTNET_API_SECRET')
    binance_trading_mode = os.getenv('BINANCE_TRADING_MODE')
    
    # Production URLs
    binance_futures_base_url = "https://fapi.binance.com"
    binance_futures_ws_url = "wss://fstream.binance.com"
    
    # Testnet URLs
    binance_futures_testnet_base_url = "https://testnet.binancefuture.com"
    binance_futures_testnet_ws_url = "wss://stream.binancefuture.com"

    # Logging configuration
    log_level = "INFO"
    log_keep_days = 30