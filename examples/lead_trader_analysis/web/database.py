#!/usr/bin/env python3
"""
Database models and operations for Lead Trader Analysis web application.
"""

import sqlite3
import os
from typing import List, Dict, Optional
from datetime import datetime

class Database:
    """Database manager for the application."""
    
    def __init__(self, db_path: str = "lead_trader_analysis.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database with required tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                api_key TEXT,
                api_secret TEXT,
                testnet BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Lead traders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lead_traders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                portfolio_id TEXT NOT NULL,
                nickname TEXT NOT NULL,
                reverse_trading BOOLEAN DEFAULT FALSE,
                reverse_coefficient REAL DEFAULT 1.0,
                margin_balance REAL DEFAULT 0.0,
                copy_balance REAL DEFAULT 10.0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, portfolio_id)
            )
        ''')
        
        # Lead trader positions table (cached/manual updates)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lead_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_trader_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                size REAL NOT NULL,
                entry_price REAL,
                mark_price REAL,
                pnl REAL,
                percentage REAL,
                copy_balance_coeff REAL DEFAULT 0.01,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_trader_id) REFERENCES lead_traders (id),
                UNIQUE(lead_trader_id, symbol)
            )
        ''')
        
        # User current positions table (from Binance API)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                size REAL NOT NULL,
                entry_price REAL,
                mark_price REAL,
                pnl REAL,
                percentage REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, symbol)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # User management
    def add_user(self, username: str, display_name: str, api_key: str = "", api_secret: str = "", testnet: bool = False) -> int:
        """Add a new user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (username, display_name, api_key, api_secret, testnet)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, display_name, api_key, api_secret, testnet))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    
    def get_users(self) -> List[Dict]:
        """Get all users."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, display_name, testnet FROM users ORDER BY display_name')
        rows = cursor.fetchall()
        conn.close()
        
        return [{"id": row[0], "username": row[1], "display_name": row[2], "testnet": bool(row[3])} for row in rows]
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0], "username": row[1], "display_name": row[2],
                "api_key": row[3], "api_secret": row[4], "testnet": bool(row[5])
            }
        return None
    
    def update_user_api(self, user_id: int, api_key: str, api_secret: str) -> bool:
        """Update user API credentials."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET api_key = ?, api_secret = ? WHERE id = ?
        ''', (api_key, api_secret, user_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    # Lead trader management
    def add_lead_trader(self, user_id: int, portfolio_id: str, nickname: str, 
                       reverse_trading: bool = False, reverse_coefficient: float = 1.0,
                       margin_balance: float = 0.0, copy_balance: float = 10.0) -> int:
        """Add a lead trader to follow."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO lead_traders (user_id, portfolio_id, nickname, reverse_trading, reverse_coefficient, margin_balance, copy_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, portfolio_id, nickname, reverse_trading, reverse_coefficient, margin_balance, copy_balance))
        
        trader_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trader_id
    
    def get_lead_traders(self, user_id: int) -> List[Dict]:
        """Get all lead traders for a user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM lead_traders WHERE user_id = ? AND is_active = TRUE
            ORDER BY nickname
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0], "user_id": row[1], "portfolio_id": row[2], "nickname": row[3],
            "reverse_trading": bool(row[4]), "reverse_coefficient": row[5], 
            "margin_balance": row[6], "copy_balance": row[7], "is_active": bool(row[8])
        } for row in rows]
    
    def update_lead_trader(self, trader_id: int, reverse_trading: bool, reverse_coefficient: float,
                          margin_balance: float = None, copy_balance: float = None) -> bool:
        """Update lead trader settings."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if margin_balance is not None and copy_balance is not None:
            cursor.execute('''
                UPDATE lead_traders 
                SET reverse_trading = ?, reverse_coefficient = ?, margin_balance = ?, copy_balance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (reverse_trading, reverse_coefficient, margin_balance, copy_balance, trader_id))
        else:
            cursor.execute('''
                UPDATE lead_traders 
                SET reverse_trading = ?, reverse_coefficient = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (reverse_trading, reverse_coefficient, trader_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def remove_lead_trader(self, trader_id: int) -> bool:
        """Remove (deactivate) a lead trader."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE lead_traders SET is_active = FALSE WHERE id = ?
        ''', (trader_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    # Position management
    def update_lead_positions(self, lead_trader_id: int, positions: List[Dict]) -> bool:
        """Update lead trader positions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Clear existing positions
        cursor.execute('DELETE FROM lead_positions WHERE lead_trader_id = ?', (lead_trader_id,))
        
        # Insert new positions
        for pos in positions:
            cursor.execute('''
                INSERT INTO lead_positions (lead_trader_id, symbol, side, size, entry_price, 
                                          mark_price, pnl, percentage, copy_balance_coeff)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (lead_trader_id, pos.get('symbol'), pos.get('side'), pos.get('size', 0),
                  pos.get('entry_price', 0), pos.get('mark_price', 0), 
                  pos.get('pnl', 0), pos.get('percentage', 0), pos.get('copy_balance_coeff', 0.01)))
        
        conn.commit()
        conn.close()
        return True
    
    def get_lead_positions(self, lead_trader_id: int) -> List[Dict]:
        """Get lead trader positions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM lead_positions WHERE lead_trader_id = ?
            ORDER BY id
        ''', (lead_trader_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0], "lead_trader_id": row[1], "symbol": row[2], "side": row[3],
            "size": row[4], "entry_price": row[5], "mark_price": row[6], 
            "pnl": row[7], "percentage": row[8], "copy_balance_coeff": row[9]
        } for row in rows]
    
    def update_user_positions(self, user_id: int, positions: List[Dict]) -> bool:
        """Update user current positions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Clear existing positions
        cursor.execute('DELETE FROM user_positions WHERE user_id = ?', (user_id,))
        
        # Insert new positions
        for pos in positions:
            cursor.execute('''
                INSERT INTO user_positions (user_id, symbol, side, size, entry_price, 
                                          mark_price, pnl, percentage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, pos.get('symbol'), pos.get('side'), pos.get('size', 0),
                  pos.get('entry_price', 0), pos.get('mark_price', 0), 
                  pos.get('pnl', 0), pos.get('percentage', 0)))
        
        conn.commit()
        conn.close()
        return True
    
    def get_user_positions(self, user_id: int) -> List[Dict]:
        """Get user current positions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM user_positions WHERE user_id = ?
            ORDER BY symbol
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0], "user_id": row[1], "symbol": row[2], "side": row[3],
            "size": row[4], "entry_price": row[5], "mark_price": row[6], 
            "pnl": row[7], "percentage": row[8]
        } for row in rows]
    
    def update_position_coefficient(self, position_id: int, copy_balance_coeff: float) -> bool:
        """Update coefficient for a specific position."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE lead_positions SET copy_balance_coeff = ? WHERE id = ?
        ''', (copy_balance_coeff, position_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def update_position_details(self, position_id: int, size: float, copy_balance_coeff: float) -> bool:
        """Update position size and coefficient."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE lead_positions 
            SET size = ?, copy_balance_coeff = ?, last_updated = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (size, copy_balance_coeff, position_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def add_single_position(self, lead_trader_id: int, symbol: str, side: str, 
                           size: float, entry_price: float, copy_balance_coeff: float) -> bool:
        """Add a single position to a lead trader."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if position already exists
        cursor.execute('''
            SELECT id FROM lead_positions WHERE lead_trader_id = ? AND symbol = ?
        ''', (lead_trader_id, symbol))
        
        if cursor.fetchone():
            # Position exists, update it
            cursor.execute('''
                UPDATE lead_positions 
                SET side = ?, size = ?, entry_price = ?, copy_balance_coeff = ?, 
                    last_updated = CURRENT_TIMESTAMP
                WHERE lead_trader_id = ? AND symbol = ?
            ''', (side, size, entry_price, copy_balance_coeff, lead_trader_id, symbol))
        else:
            # New position
            cursor.execute('''
                INSERT INTO lead_positions (lead_trader_id, symbol, side, size, entry_price, 
                                          mark_price, pnl, percentage, copy_balance_coeff)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (lead_trader_id, symbol, side, size, entry_price, entry_price, 0, 0, copy_balance_coeff))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def remove_position(self, position_id: int) -> bool:
        """Remove a position."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM lead_positions WHERE id = ?', (position_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success