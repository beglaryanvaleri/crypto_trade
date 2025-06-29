"""
Step 3: Analyze liquidations with advanced metrics and filters.
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Configuration - Change these parameters to filter liquidations
# Step 1: Initial quick filters (applied before expensive calculations)
MIN_USDT_VALUE_INITIAL = 10000  # Initial filter - only process liquidations >= $100k
MIN_PRICE_INITIAL = 0.01        # Initial filter - avoid very cheap coins

# Step 2: Advanced filters (applied after calculating indicators)
MIN_VOLUME_RATIO = 0.5          # Min liquidation_usdt / mean_volume_usdt ratio (set None to disable)
MAX_VOLUME_RATIO = None # 2.0          # Min liquidation_usdt / mean_volume_usdt ratio (set None to disable)
MIN_CANDLE_RATIO = 0.1        # Min liquidation_usdt / candle_volume_usdt ratio (set None to disable)
MAX_CANDLE_RATIO = None       # Max liquidation_usdt / candle_volume_usdt ratio (set None to disable)
MIN_VOLATILITY = 0.06           # Min daily volatility (0.02 = 2%, set None to disable)
MAX_VOLATILITY = None # 0.20           # Max daily volatility (0.20 = 20%, set None to disable)
VOLUME_LOOKBACK_HOURS = 24      # Hours to look back for mean volume calculation

# Files
LIQUIDATION_FILE = '../data/liquidations/liquidations_live_20250624_061249.jsonl'
INFO_FILE = 'liquidation_info.json'
CANDLES_DIR = 'candles'
OUTPUT_FILE = 'filtered_liquidations.csv'


def load_liquidations():
    """Load liquidation data."""
    liquidations = []
    with open(LIQUIDATION_FILE, 'r') as f:
        for line in f:
            data = json.loads(line)
            # Handle both usdt_amount and usd_amount
            if 'usdt_amount' in data:
                data['usd_amount'] = data['usdt_amount']
            liquidations.append(data)
    
    df = pd.DataFrame(liquidations)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


def load_candle_data(symbol):
    """Load candle data for a symbol."""
    file_path = Path(CANDLES_DIR) / f"{symbol}_1m.csv"
    if not file_path.exists():
        return None
    
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['volume_usdt'] = df['volume'] * df['close']  # Volume in USDT
    return df


def calculate_volatility(candles_df, lookback_hours=24):
    """Calculate volatility (standard deviation of returns)."""
    if len(candles_df) < lookback_hours * 60:  # Not enough data
        return np.nan
    
    # Get last N hours of data
    recent_candles = candles_df.tail(lookback_hours * 60)
    
    # Calculate returns
    returns = recent_candles['close'].pct_change().dropna()
    
    # Daily volatility (annualized)
    volatility = returns.std() * np.sqrt(1440)  # 1440 minutes in a day
    return volatility


def calculate_mean_volume(candles_df, lookback_hours=24):
    """Calculate mean volume in USDT over lookback period."""
    if len(candles_df) < lookback_hours * 60:
        return np.nan
    
    recent_candles = candles_df.tail(lookback_hours * 60)
    return recent_candles['volume_usdt'].mean()


def apply_initial_filters(liquidations_df):
    """Apply quick initial filters before expensive calculations."""
    initial_count = len(liquidations_df)
    print(f"Applying initial filters to {initial_count:,} liquidations...")
    
    # Filter by USDT value
    if MIN_USDT_VALUE_INITIAL is not None:
        liquidations_df = liquidations_df[liquidations_df['usd_amount'] >= MIN_USDT_VALUE_INITIAL]
        print(f"After min USDT value (${MIN_USDT_VALUE_INITIAL:,}): {len(liquidations_df):,} ({len(liquidations_df)/initial_count:.1%})")
    
    # Filter by average price (rough filter using avg_price from liquidation data)
    if MIN_PRICE_INITIAL is not None:
        liquidations_df = liquidations_df[liquidations_df['avg_price'] >= MIN_PRICE_INITIAL]
        print(f"After min price (${MIN_PRICE_INITIAL}): {len(liquidations_df):,} ({len(liquidations_df)/initial_count:.1%})")
    
    print(f"Will calculate indicators for {len(liquidations_df):,} liquidations (reduced by {(1-len(liquidations_df)/initial_count):.1%})")
    return liquidations_df


def add_market_indicators(liquidations_df):
    """Add market indicators to liquidations."""
    indicators = []
    
    print(f"\nCalculating indicators for {len(liquidations_df):,} liquidations...")
    
    for idx, row in liquidations_df.iterrows():
        symbol = row['symbol']
        liq_timestamp = row['timestamp']
        
        # Load candle data
        candles = load_candle_data(symbol)
        
        if candles is None:
            # No candle data available
            indicators.append({
                'volatility': np.nan,
                'mean_volume_usdt': np.nan,
                'volume_ratio': np.nan,
                'candle_volume_usdt': np.nan,
                'candle_ratio': np.nan,
                'price_at_liquidation': np.nan,
                'has_data': False
            })
            continue
        
        # Find candles up to liquidation time
        pre_liquidation = candles[candles['timestamp'] <= liq_timestamp]
        
        if len(pre_liquidation) == 0:
            indicators.append({
                'volatility': np.nan,
                'mean_volume_usdt': np.nan,
                'volume_ratio': np.nan,
                'candle_volume_usdt': np.nan,
                'candle_ratio': np.nan,
                'price_at_liquidation': np.nan,
                'has_data': False
            })
            continue
        
        # Calculate indicators
        volatility = calculate_volatility(pre_liquidation, VOLUME_LOOKBACK_HOURS)
        mean_volume = calculate_mean_volume(pre_liquidation, VOLUME_LOOKBACK_HOURS)
        
        # Volume ratio (liquidation vs mean volume)
        volume_ratio = row['usd_amount'] / mean_volume if mean_volume > 0 else np.nan
        
        # Price at liquidation time
        price_at_liq = pre_liquidation.iloc[-1]['close'] if len(pre_liquidation) > 0 else np.nan
        
        # Candle ratio (liquidation vs exact candle volume)
        # Find the exact candle when liquidation occurred
        exact_candle = pre_liquidation[pre_liquidation['timestamp'] == liq_timestamp]
        if len(exact_candle) == 0:
            # If exact timestamp not found, get closest candle
            closest_idx = (pre_liquidation['timestamp'] - liq_timestamp).abs().idxmin()
            exact_candle = pre_liquidation.loc[[closest_idx]]
        
        candle_volume_usdt = exact_candle.iloc[0]['volume_usdt'] if len(exact_candle) > 0 else 0
        candle_ratio = row['usd_amount'] / candle_volume_usdt if candle_volume_usdt > 0 else np.nan
        
        indicators.append({
            'volatility': volatility,
            'mean_volume_usdt': mean_volume,
            'volume_ratio': volume_ratio,
            'candle_volume_usdt': candle_volume_usdt,
            'candle_ratio': candle_ratio,
            'price_at_liquidation': price_at_liq,
            'has_data': True
        })
        
        if (idx + 1) % 1000 == 0:
            print(f"  Processed {idx + 1} liquidations...")
    
    # Add indicators to dataframe
    indicators_df = pd.DataFrame(indicators)
    result_df = pd.concat([liquidations_df.reset_index(drop=True), indicators_df], axis=1)
    
    return result_df


def apply_advanced_filters(df):
    """Apply advanced filters after calculating indicators."""
    initial_count = len(df)
    print(f"\nApplying advanced filters to {initial_count:,} liquidations...")
    
    # Filter 1: Has market data
    df = df[df['has_data'] == True]
    print(f"After requiring market data: {len(df):,} ({len(df)/initial_count:.1%})")
    
    # Filter 2: Volume ratio
    if MIN_VOLUME_RATIO is not None:
        df = df[df['volume_ratio'] >= MIN_VOLUME_RATIO]
        print(f"After min volume ratio ({MIN_VOLUME_RATIO}x): {len(df):,} ({len(df)/initial_count:.1%})")

    if MAX_VOLUME_RATIO is not None:
        df = df[df['volume_ratio'] <= MAX_VOLUME_RATIO]
        print(f"After max volume ratio ({MAX_VOLUME_RATIO}x): {len(df):,} ({len(df)/initial_count:.1%})")

    # Filter 3: Candle ratio
    if MIN_CANDLE_RATIO is not None:
        df = df[df['candle_ratio'] >= MIN_CANDLE_RATIO]
        print(f"After min candle ratio ({MIN_CANDLE_RATIO}x): {len(df):,} ({len(df)/initial_count:.1%})")

    if MAX_CANDLE_RATIO is not None:
        df = df[df['candle_ratio'] <= MAX_CANDLE_RATIO]
        print(f"After max candle ratio ({MAX_CANDLE_RATIO}x): {len(df):,} ({len(df)/initial_count:.1%})")

    
    # Filter 4: Volatility range
    if MIN_VOLATILITY is not None:
        df = df[df['volatility'] >= MIN_VOLATILITY]
        print(f"After min volatility ({MIN_VOLATILITY:.1%}): {len(df):,} ({len(df)/initial_count:.1%})")
    
    if MAX_VOLATILITY is not None:
        df = df[df['volatility'] <= MAX_VOLATILITY]
        print(f"After max volatility ({MAX_VOLATILITY:.1%}): {len(df):,} ({len(df)/initial_count:.1%})")
    
    return df


def analyze_results(df):
    """Show all filtered liquidations sorted by timestamp."""
    if len(df) == 0:
        print("\nNo liquidations passed all filters!")
        return
    
    print(f"\n{'='*120}")
    print(f"FILTERED LIQUIDATIONS ({len(df):,} total)")
    print(f"{'='*120}")
    
    # Sort by timestamp
    df_sorted = df.sort_values('timestamp')
    
    # Print header
    print(f"{'Time':<20} {'Symbol':<12} {'Side':<5} {'USDT Value':>12} {'Vol Ratio':>9} {'Candle Ratio':>12} {'Volatility':>10} {'Price':>10}")
    print("-" * 135)
    
    # Print all liquidations
    for _, row in df_sorted.iterrows():
        time_str = row['datetime'].strftime('%Y-%m-%d %H:%M:%S')
        print(f"{time_str:<20} {row['symbol']:<12} {row['side']:<5} "
              f"${row['usd_amount']:>11,.0f} {row['volume_ratio']:>8.1f}x "
              f"{row['candle_ratio']:>11.1f}x {row['volatility']:>9.1%} ${row['price_at_liquidation']:>9.4f}")
    
    print(f"\nSummary: {len(df):,} liquidations, Total: ${df['usd_amount'].sum():,.0f}")


def main():
    print("Loading liquidation data...")
    liquidations_df = load_liquidations()
    
    print("Applying initial filters...")
    initial_filtered_df = apply_initial_filters(liquidations_df)
    
    print("Adding market indicators...")
    enhanced_df = add_market_indicators(initial_filtered_df)
    
    print("Applying advanced filters...")
    filtered_df = apply_advanced_filters(enhanced_df)
    
    # Save results
    if len(filtered_df) > 0:
        # Select relevant columns for output
        output_columns = [
            'timestamp', 'datetime', 'symbol', 'side', 'quantity', 'price', 'avg_price',
            'usd_amount', 'volatility', 'mean_volume_usdt', 'volume_ratio', 
            'candle_volume_usdt', 'candle_ratio', 'price_at_liquidation'
        ]
        
        output_df = filtered_df[output_columns].copy()
        output_df = output_df.sort_values('usd_amount', ascending=False)
        
        output_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSaved {len(output_df)} filtered liquidations to {OUTPUT_FILE}")
    
    # Analysis
    analyze_results(filtered_df)


if __name__ == "__main__":
    main()