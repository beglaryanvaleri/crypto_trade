#!/usr/bin/env python3
"""
Flask web application for Binance Lead Trader Analysis.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from database import Database
from typing import List, Dict

# Try to import Binance interface
try:
    from src.exchanges.binance import BinanceFuturesInterface
    BINANCE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Binance interface not available: {e}")
    BINANCE_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production

# Initialize database
db = Database()

@app.route('/')
def index():
    """Main index page with global user selection."""
    return render_template('index.html')

@app.route('/api/user_positions/<int:user_id>')
def get_user_positions(user_id: int):
    """Get current user positions."""
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"})
        
        if not user['api_key'] or not user['api_secret']:
            return jsonify({"success": False, "error": "API credentials not configured for user"})
        
        if not BINANCE_AVAILABLE:
            return jsonify({"success": False, "error": "Binance interface not available"})
        
        # Create Binance interface
        mode = "testnet" if user['testnet'] else "live"
        binance = BinanceFuturesInterface(
            api_key=user['api_key'],
            api_secret=user['api_secret'],
            testnet_api_key=user['api_key'] if user['testnet'] else None,
            testnet_api_secret=user['api_secret'] if user['testnet'] else None,
            mode=mode
        )
        
        # Get positions from Binance
        binance_positions = binance.get_all_positions()
        
        print(f"Raw Binance positions for user {user_id}: {binance_positions}")
        
        # Convert to our format
        positions = []
        for pos in binance_positions:
            # Convert Binance position sides to our format
            side = pos['side']
            if side == 'LONG':
                side = 'BUY'
            elif side == 'SHORT':
                side = 'SELL'
            
            positions.append({
                'symbol': pos['symbol'],
                'side': side,
                'size': abs(pos['amount']),
                'entry_price': pos['entry_price'],
                'mark_price': pos['mark_price'],
                'pnl': pos['unrealized_pnl'],
                'percentage': (pos['unrealized_pnl'] / (pos['entry_price'] * abs(pos['amount'])) * 100) if pos['entry_price'] > 0 and pos['amount'] != 0 else 0
            })
        
        # Update database cache
        db.update_user_positions(user_id, positions)
        
        return jsonify({"success": True, "positions": positions})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/lead_traders_overview/<int:user_id>')
def get_lead_traders_overview(user_id: int):
    """Get all lead traders and their positions for dashboard overview."""
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"})
        
        # Get all lead traders for this user
        lead_traders = db.get_lead_traders(user_id)
        
        # Get positions for each trader and calculate reverse trades
        overview_data = []
        for trader in lead_traders:
            print(f"Processing trader {trader['id']}: reverse={trader['reverse_trading']}, coeff={trader['reverse_coefficient']}")
            positions = db.get_lead_positions(trader['id'])
            
            # Calculate reverse trades for each position
            calculated_positions = []
            for pos in positions:
                # Calculate based on example: 
                # lead trader BUY 1 BTC, coefficient 0.01 = 0.01 BTC for $10
                # reverse=True, reverse_coeff=5 = 0.01 * 5 = 0.05 BTC SELL
                
                # Calculate copy balance size using copy balance coefficient
                copy_balance_size = pos['size'] * pos['copy_balance_coeff']
                
                # Calculate suggested coefficient if margin balance is set
                suggested_coeff = 0.01  # Default
                if trader['margin_balance'] > 0 and trader['copy_balance'] > 0:
                    suggested_coeff = trader['copy_balance'] / trader['margin_balance']
                
                if trader['reverse_trading']:
                    calculated_size = copy_balance_size * trader['reverse_coefficient']
                    calculated_side = 'SELL' if pos['side'] == 'BUY' else 'BUY'
                else:
                    calculated_size = copy_balance_size
                    calculated_side = pos['side']
                
                calculated_positions.append({
                    **pos,
                    'calculated_size': round(calculated_size, 5),
                    'calculated_side': calculated_side,
                    'copy_balance_size': round(copy_balance_size, 5),
                    'suggested_coeff': round(suggested_coeff, 5)
                })
            
            overview_data.append({
                **trader,
                'positions': calculated_positions,
                'position_count': len(calculated_positions)
            })
        
        return jsonify({
            "success": True, 
            "lead_traders": overview_data,
            "total_traders": len(overview_data)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/update_position_coefficient', methods=['POST'])
def update_position_coefficient():
    """Update coefficient for a specific position."""
    try:
        position_id = int(request.json['position_id'])
        coefficient = float(request.json['coefficient'])
        
        success = db.update_position_coefficient(position_id, coefficient)
        
        if success:
            return jsonify({"success": True, "message": "Position coefficient updated"})
        else:
            return jsonify({"success": False, "error": "Failed to update coefficient"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/update_position', methods=['POST'])
def update_position():
    """Update position details (size, coefficient)."""
    try:
        position_id = int(request.json['position_id'])
        size = float(request.json.get('size', 0))
        coefficient = float(request.json.get('coefficient', 0.01))
        
        success = db.update_position_details(position_id, size, coefficient)
        
        if success:
            return jsonify({"success": True, "message": "Position updated"})
        else:
            return jsonify({"success": False, "error": "Failed to update position"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/add_position', methods=['POST'])
def add_position():
    """Add new position to a lead trader."""
    try:
        lead_trader_id = int(request.json['lead_trader_id'])
        symbol = request.json['symbol'].upper()
        side = request.json['side'].upper()
        size = float(request.json['size'])
        entry_price = float(request.json.get('entry_price', 0))
        coefficient = float(request.json.get('coefficient', 0.01))
        
        success = db.add_single_position(
            lead_trader_id, symbol, side, size, entry_price, coefficient
        )
        
        if success:
            return jsonify({"success": True, "message": "Position added"})
        else:
            return jsonify({"success": False, "error": "Failed to add position"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/remove_position', methods=['POST'])
def remove_position():
    """Remove a position."""
    try:
        position_id = int(request.json['position_id'])
        
        success = db.remove_position(position_id)
        
        if success:
            return jsonify({"success": True, "message": "Position removed"})
        else:
            return jsonify({"success": False, "error": "Failed to remove position"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/update_trader_settings', methods=['POST'])
def update_trader_settings():
    """Update trader settings (margin balance, copy balance, reverse settings)."""
    try:
        trader_id = int(request.json['trader_id'])
        margin_balance = float(request.json.get('margin_balance', 0))
        copy_balance = float(request.json.get('copy_balance', 10))
        reverse_trading = bool(request.json.get('reverse_trading', False))
        reverse_coefficient = float(request.json.get('reverse_coefficient', 1.0))
        
        print(f"Updating trader {trader_id}: margin={margin_balance}, copy={copy_balance}, reverse={reverse_trading}, coeff={reverse_coefficient}")
        
        success = db.update_lead_trader(
            trader_id, reverse_trading, reverse_coefficient, margin_balance, copy_balance
        )
        
        print(f"Update result: {success}")
        
        if success:
            return jsonify({"success": True, "message": "Trader settings updated"})
        else:
            return jsonify({"success": False, "error": "Failed to update trader settings"})
            
    except Exception as e:
        print(f"Error updating trader settings: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/users')
def get_users_api():
    """Get all users for global user selection."""
    try:
        users = db.get_users()
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/trade_summary/<int:user_id>')
def get_trade_summary(user_id: int):
    """Get aggregated trade summary comparing calculated trades vs actual positions."""
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"})
        
        # Get all lead traders for this user
        lead_traders = db.get_lead_traders(user_id)
        print(f"Found {len(lead_traders)} lead traders for user {user_id}")
        
        # Aggregate calculated positions by symbol
        calculated_positions = {}
        for trader in lead_traders:
            positions = db.get_lead_positions(trader['id'])
            print(f"Trader {trader['id']} ({trader['nickname']}) has {len(positions)} positions")
            
            for pos in positions:
                symbol = pos['symbol']
                
                # Calculate copy balance size
                copy_balance_size = pos['size'] * pos['copy_balance_coeff']
                
                # Calculate final trade size and side
                if trader['reverse_trading']:
                    calculated_size = copy_balance_size * trader['reverse_coefficient']
                    calculated_side = 'SELL' if pos['side'] == 'BUY' else 'BUY'
                else:
                    calculated_size = copy_balance_size
                    calculated_side = pos['side']
                
                # Ensure we have valid calculated side
                if calculated_side not in ['BUY', 'SELL']:
                    continue  # Skip positions with invalid sides
                
                # Aggregate by symbol
                if symbol not in calculated_positions:
                    calculated_positions[symbol] = {'BUY': 0, 'SELL': 0}
                
                calculated_positions[symbol][calculated_side] += calculated_size
        
        # Get user's actual positions
        actual_positions = db.get_user_positions(user_id)
        print(f"User has {len(actual_positions)} actual positions")
        
        actual_by_symbol = {}
        for pos in actual_positions:
            symbol = pos['symbol']
            side = pos['side']
            
            # Ensure we have valid side values
            if side not in ['BUY', 'SELL']:
                continue  # Skip positions with invalid sides
                
            if symbol not in actual_by_symbol:
                actual_by_symbol[symbol] = {'BUY': 0, 'SELL': 0}
            actual_by_symbol[symbol][side] += pos['size']
        
        # Create summary comparison
        summary = []
        all_symbols = set(calculated_positions.keys()) | set(actual_by_symbol.keys())
        print(f"All symbols found: {all_symbols}")
        print(f"Calculated positions: {calculated_positions}")
        print(f"Actual positions: {actual_by_symbol}")
        
        for symbol in all_symbols:
            calc = calculated_positions.get(symbol, {'BUY': 0, 'SELL': 0})
            actual = actual_by_symbol.get(symbol, {'BUY': 0, 'SELL': 0})
            
            # Calculate net positions
            calc_net = calc['BUY'] - calc['SELL']
            actual_net = actual['BUY'] - actual['SELL']
            
            # Calculate difference
            difference_net = calc_net - actual_net
            
            # Determine sides and sizes for display
            calc_side = 'BUY' if calc_net >= 0 else 'SELL'
            calc_size = abs(calc_net)
            
            actual_side = 'BUY' if actual_net >= 0 else 'SELL'
            actual_size = abs(actual_net)
            
            difference_side = 'BUY' if difference_net >= 0 else 'SELL'
            difference_abs = abs(difference_net)
            
            # Calculate percentage difference (difference / calculated size * 100)
            # Handle zero calculated size safely
            if calc_size > 0:
                difference_percent = round((difference_abs / calc_size) * 100, 2)
            else:
                # If no calculated size but there's actual size, show as 100% difference
                difference_percent = 100.0 if actual_size > 0 else 0.0
            
            # Include position if there's any calculated size, actual size, or difference
            if calc_size > 0 or actual_size > 0 or difference_abs > 0:
                summary.append({
                    'symbol': symbol,
                    'calculated_side': calc_side,
                    'calculated_size': calc_size,
                    'actual_side': actual_side,
                    'actual_size': actual_size,
                    'difference_side': difference_side,
                    'difference_abs': difference_abs,
                    'difference_percent': difference_percent
                })
                print(f"Added to summary: {symbol} - calc:{calc_size} {calc_side}, actual:{actual_size} {actual_side}, diff:{difference_abs} {difference_side} ({difference_percent}%)")
        
        # Sort by symbol
        summary.sort(key=lambda x: x['symbol'])
        
        return jsonify({
            "success": True,
            "summary": summary,
            "total_symbols": len(summary)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/users')
def manage_users():
    """User management page."""
    users = db.get_users()
    return render_template('users.html', users=users)

@app.route('/add_user', methods=['POST'])
def add_user():
    """Add a new user."""
    try:
        username = request.form['username']
        display_name = request.form['display_name']
        api_key = request.form.get('api_key', '')
        api_secret = request.form.get('api_secret', '')
        testnet = 'testnet' in request.form
        
        user_id = db.add_user(username, display_name, api_key, api_secret, testnet)
        flash(f'User {display_name} added successfully!', 'success')
        
    except Exception as e:
        flash(f'Error adding user: {e}', 'error')
    
    return redirect(url_for('manage_users'))

@app.route('/lead_traders/<int:user_id>')
def manage_lead_traders(user_id: int):
    """Lead trader management page."""
    user = db.get_user_by_id(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('index'))
    
    lead_traders = db.get_lead_traders(user_id)
    return render_template('lead_traders.html', user=user, lead_traders=lead_traders)

@app.route('/add_lead_trader', methods=['POST'])
def add_lead_trader():
    """Add a new lead trader."""
    try:
        user_id = int(request.form['user_id'])
        portfolio_id = request.form['portfolio_id']
        nickname = request.form['nickname']
        reverse_trading = 'reverse_trading' in request.form
        reverse_coefficient = float(request.form.get('reverse_coefficient', 1.0))
        
        trader_id = db.add_lead_trader(
            user_id, portfolio_id, nickname, reverse_trading, reverse_coefficient
        )
        flash(f'Lead trader {nickname} added successfully!', 'success')
        
    except Exception as e:
        flash(f'Error adding lead trader: {e}', 'error')
    
    return redirect(url_for('manage_lead_traders', user_id=request.form['user_id']))

@app.route('/update_lead_trader', methods=['POST'])
def update_lead_trader():
    """Update lead trader settings."""
    try:
        trader_id = int(request.form['trader_id'])
        user_id = int(request.form['user_id'])
        reverse_trading = 'reverse_trading' in request.form
        reverse_coefficient = float(request.form['reverse_coefficient'])
        
        success = db.update_lead_trader(
            trader_id, reverse_trading, reverse_coefficient
        )
        
        if success:
            flash('Lead trader updated successfully!', 'success')
        else:
            flash('Failed to update lead trader', 'error')
        
    except Exception as e:
        flash(f'Error updating lead trader: {e}', 'error')
    
    return redirect(url_for('manage_lead_traders', user_id=user_id))

@app.route('/remove_lead_trader', methods=['POST'])
def remove_lead_trader():
    """Remove a lead trader."""
    try:
        trader_id = int(request.form['trader_id'])
        user_id = int(request.form['user_id'])
        
        success = db.remove_lead_trader(trader_id)
        
        if success:
            flash('Lead trader removed successfully!', 'success')
        else:
            flash('Failed to remove lead trader', 'error')
        
    except Exception as e:
        flash(f'Error removing lead trader: {e}', 'error')
    
    return redirect(url_for('manage_lead_traders', user_id=user_id))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)