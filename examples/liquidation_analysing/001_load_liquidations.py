"""
Step 1: Load liquidation data and extract time range and symbols.
"""
import json
from datetime import datetime
from pathlib import Path

# Configuration
DATA_FILE = '../data/liquidations/liquidations_live_20250624_061249.jsonl'
OUTPUT_INFO_FILE = 'liquidation_info.json'


def main():
    print("Loading liquidation data...")
    
    # Load all liquidations
    liquidations = []
    with open(DATA_FILE, 'r') as f:
        for line in f:
            liquidations.append(json.loads(line))
    
    print(f"Loaded {len(liquidations)} liquidations")
    
    # Extract unique symbols
    symbols = sorted(list(set(liq['symbol'] for liq in liquidations)))
    print(f"Found {len(symbols)} unique symbols")
    
    # Find time range
    timestamps = [liq['timestamp'] for liq in liquidations]
    start_timestamp = min(timestamps)
    end_timestamp = max(timestamps)
    
    start_time = datetime.fromtimestamp(start_timestamp / 1000)
    end_time = datetime.fromtimestamp(end_timestamp / 1000)
    
    print(f"Time range: {start_time} to {end_time}")
    print(f"Duration: {end_time - start_time}")
    
    # Save info for next steps
    info = {
        'start_timestamp': start_timestamp,
        'end_timestamp': end_timestamp,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'symbols': symbols,
        'symbol_count': len(symbols),
        'liquidation_count': len(liquidations),
        'data_file': DATA_FILE
    }
    
    with open(OUTPUT_INFO_FILE, 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"\nSaved info to {OUTPUT_INFO_FILE}")
    
    # Show sample of symbols
    print(f"\nFirst 10 symbols: {symbols[:10]}")
    print(f"Last 10 symbols: {symbols[-10:]}")


if __name__ == "__main__":
    main()