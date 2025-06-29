#!/usr/bin/env python3
"""
Parser for Binance Copy Trading lead trader portfolio HTML files.
Extracts structured data from saved portfolio pages.
"""

import json
import re
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TraderPerformance:
    """Lead trader performance metrics."""
    roi: float
    pnl: float
    max_drawdown: float
    win_rate: float
    total_orders: int
    winning_orders: int
    sharpe_ratio: Optional[float] = None


@dataclass
class PortfolioInfo:
    """Portfolio information."""
    portfolio_id: str
    nickname: str
    margin_balance: float
    aum: float
    current_copiers: int
    max_copiers: int
    profit_sharing_rate: float
    copier_pnl: float


@dataclass
class TraderData:
    """Complete trader data structure."""
    portfolio_info: PortfolioInfo
    performance: TraderPerformance
    raw_data: Dict
    parsed_at: datetime


class BinancePortfolioParser:
    """Parser for Binance Copy Trading portfolio HTML files."""
    
    def __init__(self):
        self.supported_periods = ["7d", "30d", "90d", "180d", "365d"]
    
    def parse_html_file(self, file_path: str) -> Optional[Dict]:
        """
        Parse a single HTML file and extract all trader data as a dictionary.
        
        Args:
            file_path: Path to the HTML file
            
        Returns:
            Dictionary with all trader information including positions
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find the script tag with app data
            app_data_script = soup.find('script', {'id': '__APP_DATA'})
            if not app_data_script:
                print(f"No __APP_DATA script found in {file_path}")
                return None
            
            # Extract JSON data
            json_text = app_data_script.string
            if not json_text:
                print(f"No JSON data found in __APP_DATA script")
                return None
            
            # Parse JSON
            app_data = json.loads(json_text)
            
            # Extract all data as dictionary
            trader_dict = self._extract_all_data(app_data, file_path)
            if not trader_dict:
                print(f"Failed to extract trader data from {file_path}")
                return None
            
            return trader_dict
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def _extract_all_data(self, app_data: Dict, file_path: str) -> Optional[Dict]:
        """Extract all trader data as a single dictionary."""
        try:
            # Navigate through the data structure
            app_state = app_data.get('appState', {})
            loader_data = app_state.get('loader', {}).get('dataByRouteId', {})
            
            # Initialize result dictionary
            result = {
                "parsed_at": datetime.now().isoformat(),
                "source_file": file_path.split('/')[-1] if '/' in file_path else file_path,
                "portfolio_id": None,
                "nickname": None,
                "margin_balance": 0,
                "aum": 0,
                "current_copiers": 0,
                "max_copiers": 0,
                "profit_sharing_rate": 0,
                "copier_pnl": 0,
                "roi": 0,
                "pnl": 0,
                "max_drawdown": 0,
                "win_rate": 0,
                "total_orders": 0,
                "winning_orders": 0,
                "sharpe_ratio": None,
                "positions": {},
                "additional_data": {}
            }
            
            # Look for data in the loader structure
            for route_id, route_data in loader_data.items():
                if 'dehydratedState' in route_data:
                    queries = route_data['dehydratedState'].get('queries', [])
                    
                    for query in queries:
                        query_key = query.get('queryKey', [])
                        state_data = query.get('state', {}).get('data', {})
                        
                        if not state_data:
                            continue
                        
                        # Portfolio detail data
                        if 'FUT_LEAD_DETAIL' in str(query_key):
                            if state_data.get('success') and state_data.get('data'):
                                data = state_data['data']
                                result.update({
                                    "portfolio_id": data.get('leadPortfolioId', data.get('portfolioId', '')),
                                    "nickname": data.get('nickname', 'Unknown'),
                                    "margin_balance": float(data.get('marginBalance', 0)),
                                    "aum": float(data.get('aumAmount', 0)),
                                    "current_copiers": int(data.get('currentCopyCount', 0)),
                                    "max_copiers": int(data.get('maxCopyCount', 0)),
                                    "profit_sharing_rate": float(data.get('profitSharingRate', 0)),
                                    "copier_pnl": float(data.get('copierPnl', 0))
                                })
                        
                        # Performance data
                        elif 'leadPortfolioPerformance' in str(query_key):
                            if state_data.get('success') and state_data.get('data'):
                                data = state_data['data']
                                result.update({
                                    "roi": float(data.get('roi', 0)),
                                    "pnl": float(data.get('pnl', 0)),
                                    "max_drawdown": float(data.get('mdd', 0)),
                                    "win_rate": float(data.get('winRate', 0)),
                                    "total_orders": int(data.get('totalOrder', 0)),
                                    "winning_orders": int(data.get('winOrders', 0)),
                                    "sharpe_ratio": float(data.get('sharpRatio', 0)) if data.get('sharpRatio') else None
                                })
                        
                        # Position data
                        elif 'position' in str(query_key).lower() or 'Position' in str(query_key):
                            if state_data.get('success') and state_data.get('data'):
                                position_data = state_data['data']
                                
                                # Convert position list to dict with symbol as key
                                if isinstance(position_data, list):
                                    positions_dict = {}
                                    for pos in position_data:
                                        if isinstance(pos, dict) and 'symbol' in pos:
                                            symbol = pos['symbol']
                                            positions_dict[symbol] = pos
                                    result["positions"] = positions_dict
                                elif isinstance(position_data, dict):
                                    # Check if it contains position list
                                    if 'otherPositionRetList' in position_data:
                                        positions_list = position_data['otherPositionRetList']
                                        positions_dict = {}
                                        for pos in positions_list:
                                            if isinstance(pos, dict) and 'symbol' in pos:
                                                symbol = pos['symbol']
                                                positions_dict[symbol] = pos
                                        result["positions"] = positions_dict
                                    else:
                                        result["positions"] = position_data
                        
                        # Store other interesting data
                        else:
                            query_name = str(query_key)
                            result["additional_data"][query_name] = state_data
            
            return result if result["portfolio_id"] else None
            
        except Exception as e:
            print(f"Error extracting all data: {e}")
            return None
    
    def _extract_trader_data(self, app_data: Dict) -> Optional[Dict]:
        """Extract structured trader data from app data JSON."""
        try:
            # Navigate through the data structure
            app_state = app_data.get('appState', {})
            loader_data = app_state.get('loader', {}).get('dataByRouteId', {})
            
            # Look for the data in the loader structure
            portfolio_info = None
            performance_data = None
            
            for route_id, route_data in loader_data.items():
                if 'dehydratedState' in route_data:
                    queries = route_data['dehydratedState'].get('queries', [])
                    
                    for query in queries:
                        query_key = query.get('queryKey', [])
                        state_data = query.get('state', {}).get('data', {})
                        
                        if not state_data:
                            continue
                        
                        # Check if this is portfolio detail data
                        if 'FUT_LEAD_DETAIL' in str(query_key):
                            if state_data.get('success') and state_data.get('data'):
                                portfolio_info = self._parse_portfolio_info(state_data['data'])
                        
                        # Check if this is performance data
                        elif 'leadPortfolioPerformance' in str(query_key):
                            if state_data.get('success') and state_data.get('data'):
                                performance_data = self._parse_performance_data(state_data['data'])
            
            if portfolio_info and performance_data:
                return {
                    'portfolio_info': portfolio_info,
                    'performance': performance_data
                }
            
            return None
            
        except Exception as e:
            print(f"Error extracting trader data: {e}")
            return None
    
    def _parse_portfolio_info(self, data: Dict) -> PortfolioInfo:
        """Parse portfolio information."""
        return PortfolioInfo(
            portfolio_id=data.get('leadPortfolioId', data.get('portfolioId', '')),
            nickname=data.get('nickname', 'Unknown'),
            margin_balance=float(data.get('marginBalance', 0)),
            aum=float(data.get('aumAmount', 0)),
            current_copiers=int(data.get('currentCopyCount', 0)),
            max_copiers=int(data.get('maxCopyCount', 0)),
            profit_sharing_rate=float(data.get('profitSharingRate', 0)),
            copier_pnl=float(data.get('copierPnl', 0))
        )
    
    def _parse_performance_data(self, data: Dict) -> TraderPerformance:
        """Parse performance data."""
        # The data should already be in the correct format from the API
        return TraderPerformance(
            roi=float(data.get('roi', 0)),
            pnl=float(data.get('pnl', 0)),
            max_drawdown=float(data.get('mdd', 0)),
            win_rate=float(data.get('winRate', 0)),
            total_orders=int(data.get('totalOrder', 0)),
            winning_orders=int(data.get('winOrders', 0)),
            sharpe_ratio=float(data.get('sharpRatio', 0)) if data.get('sharpRatio') else None
        )
    
    def get_summary(self, trader_dict: Dict) -> str:
        """Generate a summary string for the trader."""
        sharpe_str = f"{trader_dict['sharpe_ratio']:.3f}" if trader_dict['sharpe_ratio'] is not None else "N/A"
        positions_count = len(trader_dict['positions'])
        
        summary = f"""
=== {trader_dict['nickname']} (ID: {trader_dict['portfolio_id']}) ===
Portfolio:
  • AUM: ${trader_dict['aum']:,.2f} USDT
  • Margin Balance: ${trader_dict['margin_balance']:,.2f} USDT
  • Current Copiers: {trader_dict['current_copiers']}/{trader_dict['max_copiers']}
  • Profit Sharing: {trader_dict['profit_sharing_rate']}%
  • Copier PnL: ${trader_dict['copier_pnl']:,.2f} USDT

7-Day Performance:
  • ROI: {trader_dict['roi']:.2f}%
  • PnL: ${trader_dict['pnl']:,.2f} USDT
  • Max Drawdown: {trader_dict['max_drawdown']:.2f}%
  • Win Rate: {trader_dict['win_rate']:.2f}% ({trader_dict['winning_orders']}/{trader_dict['total_orders']})
  • Sharpe Ratio: {sharpe_str}

Positions: {positions_count} open positions
Parsed at: {trader_dict['parsed_at']}
"""
        return summary