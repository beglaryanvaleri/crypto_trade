"""
Step 2: Download 1-minute candles for all symbols in the liquidation time range.
"""
import json
import csv
import time
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from exchanges.binance import BinanceFuturesInterface
from config import Config
from utils.logger import setup_logger, get_logger

setup_logger(log_level=Config.log_level)
logger = get_logger('download_candles')

# Configuration
INFO_FILE = 'liquidation_info.json'
OUTPUT_DIR = 'candles'
INTERVAL = '1m'
DELAY_BETWEEN_REQUESTS = 0.2  # seconds between API calls to avoid rate limits
PROGRESS_FILE = 'download_progress.json'


def save_candles_to_csv(symbol, candles, output_dir):
    """Save candles to CSV file."""
    filename = f"{output_dir}/{symbol}_1m.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trades'])
        
        for candle in candles:
            writer.writerow([
                candle['timestamp'],
                candle['open'],
                candle['high'],
                candle['low'],
                candle['close'],
                candle['volume'],
                candle['quote_volume'],
                candle['trades']
            ])
    
    return filename


def load_progress():
    """Load download progress."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'completed': [], 'failed': []}


def save_progress(progress):
    """Save download progress."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)


def main():
    # Load liquidation info
    with open(INFO_FILE, 'r') as f:
        info = json.load(f)
    
    symbols = info['symbols']
    # Start 1 day earlier to calculate baseline metrics
    one_day_ms = 24 * 60 * 60 * 1000  # 1 day in milliseconds
    start_time = info['start_timestamp'] - one_day_ms
    end_time = info['end_timestamp']
    
    # Load progress
    progress = load_progress()
    completed = progress['completed']
    failed = progress['failed']
    
    # Filter out already completed symbols
    remaining_symbols = [s for s in symbols if s not in completed]
    
    print(f"Total symbols: {len(symbols)}")
    print(f"Already completed: {len(completed)}")
    print(f"Remaining: {len(remaining_symbols)}")
    print(f"Liquidation time: {info['start_time']} to {info['end_time']}")
    
    from datetime import datetime
    extended_start = datetime.fromtimestamp(start_time / 1000).isoformat()
    print(f"Download time: {extended_start} to {info['end_time']} (includes 1 day before)")
    
    if len(remaining_symbols) == 0:
        print("\nAll symbols already downloaded!")
        return
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Initialize interface
    interface = BinanceFuturesInterface(
        api_key=Config.binance_api_key,
        api_secret=Config.binance_secret_key,
        testnet_api_key=Config.binance_testnet_api_key,
        testnet_api_secret=Config.binance_testnet_secret_key,
        mode='live'  # Use live mode for historical data
    )
    
    # Download candles for each remaining symbol
    start_download_time = time.time()
    
    for i, symbol in enumerate(remaining_symbols):
        try:
            print(f"\n[{i+1}/{len(remaining_symbols)}] Downloading {symbol}...", end='', flush=True)
            
            # Get historical klines
            candles = interface.get_historical_klines(
                symbol=symbol,
                interval=INTERVAL,
                start_time=start_time,
                end_time=end_time
            )
            
            if candles:
                filename = save_candles_to_csv(symbol, candles, OUTPUT_DIR)
                print(f" ✓ Saved {len(candles)} candles")
                completed.append(symbol)
            else:
                print(f" ✗ No data")
                failed.append(symbol)
            
            # Save progress
            save_progress({'completed': completed, 'failed': failed})
            
            # Estimate time remaining
            if i > 0:
                elapsed = time.time() - start_download_time
                avg_time_per_symbol = elapsed / (i + 1)
                remaining_time = avg_time_per_symbol * (len(remaining_symbols) - i - 1)
                print(f"  ETA: {int(remaining_time / 60)} minutes remaining")
            
            # Small delay to avoid rate limits
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f" ✗ Error: {e}")
            failed.append(symbol)
            save_progress({'completed': completed, 'failed': failed})
            logger.error(f"Failed to download {symbol}: {e}")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Download complete!")
    print(f"Total time: {int((time.time() - start_download_time) / 60)} minutes")
    print(f"Successfully downloaded: {len(completed)} symbols")
    print(f"Failed: {len(failed)} symbols")
    
    if failed:
        print(f"\nFailed symbols: {failed[:10]}...")  # Show first 10
        
        # Save failed symbols for retry
        with open(f"{OUTPUT_DIR}/failed_symbols.json", 'w') as f:
            json.dump(failed, f)


if __name__ == "__main__":
    main()