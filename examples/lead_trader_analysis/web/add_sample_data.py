#!/usr/bin/env python3
"""
Add sample data for testing the lead trader analysis application.
"""

from database import Database

def add_sample_data():
    """Add sample users, lead traders, and positions for testing."""
    db = Database()
    
    # Add sample user
    print("Adding sample user...")
    user_id = db.add_user(
        username="demo_user",
        display_name="Demo User", 
        api_key="demo_api_key",
        api_secret="demo_api_secret",
        testnet=True
    )
    print(f"Created user with ID: {user_id}")
    
    # Add sample lead traders
    print("Adding sample lead traders...")
    
    # Trader 1: Regular trading
    trader1_id = db.add_lead_trader(
        user_id=user_id,
        portfolio_id="4574016324038903041",
        nickname="九木夏",
        reverse_trading=False,
        reverse_coefficient=1.0,
        margin_balance=1000.0,
        copy_balance=10.0
    )
    print(f"Created trader 1 with ID: {trader1_id}")
    
    # Trader 2: Reverse trading
    trader2_id = db.add_lead_trader(
        user_id=user_id,
        portfolio_id="4581885897857515521", 
        nickname="27直走",
        reverse_trading=True,
        reverse_coefficient=5.0,
        margin_balance=500.0,
        copy_balance=15.0
    )
    print(f"Created trader 2 with ID: {trader2_id}")
    
    # Add sample positions for trader 1
    print("Adding sample positions for trader 1...")
    trader1_positions = [
        {
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'size': 1.0,
            'entry_price': 65000.0,
            'mark_price': 66000.0,
            'pnl': 1000.0,
            'percentage': 1.54,
            'copy_balance_coeff': 0.01
        },
        {
            'symbol': 'ETHUSDT',
            'side': 'SELL',
            'size': 5.0,
            'entry_price': 3200.0,
            'mark_price': 3150.0,
            'pnl': 250.0,
            'percentage': 1.56,
            'copy_balance_coeff': 0.02
        }
    ]
    db.update_lead_positions(trader1_id, trader1_positions)
    
    # Add sample positions for trader 2
    print("Adding sample positions for trader 2...")
    trader2_positions = [
        {
            'symbol': 'ADAUSDT',
            'side': 'BUY',
            'size': 1000.0,
            'entry_price': 0.45,
            'mark_price': 0.47,
            'pnl': 20.0,
            'percentage': 4.44,
            'copy_balance_coeff': 0.05
        },
        {
            'symbol': 'SOLUSDT',
            'side': 'SELL',
            'size': 10.0,
            'entry_price': 180.0,
            'mark_price': 175.0,
            'pnl': 50.0,
            'percentage': 2.78,
            'copy_balance_coeff': 0.01
        }
    ]
    db.update_lead_positions(trader2_id, trader2_positions)
    
    print("\n✅ Sample data added successfully!")
    print("\nSample data includes:")
    print(f"• User: {user_id} (Demo User)")
    print(f"• Lead Trader 1: {trader1_id} (九木夏) - Normal trading, 2 positions")
    print(f"• Lead Trader 2: {trader2_id} (27直走) - Reverse trading (5x), 2 positions")
    print("\nYou can now test the dashboard with real data!")

if __name__ == "__main__":
    add_sample_data()