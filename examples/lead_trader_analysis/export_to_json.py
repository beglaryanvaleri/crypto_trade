#!/usr/bin/env python3
"""
Export all trader account information and positions to JSON format.
"""

import os
import json
from binance_portfolio_parser import BinancePortfolioParser
from datetime import datetime


def export_trader_data():
    """Export all available trader data to JSON files."""
    
    # Path to the portfolio data
    portfolio_dir = os.path.expanduser("~/Downloads/binance_portfolio")
    
    if not os.path.exists(portfolio_dir):
        print(f"Error: Directory {portfolio_dir} not found")
        return
    
    # List HTML files
    html_files = [f for f in os.listdir(portfolio_dir) if f.endswith('.html')]
    
    if not html_files:
        print(f"No HTML files found in {portfolio_dir}")
        return
    
    print(f"Processing {len(html_files)} trader portfolio files...")
    
    # Initialize parser
    parser = BinancePortfolioParser()
    
    all_traders_data = []
    
    for file_name in html_files:
        file_path = os.path.join(portfolio_dir, file_name)
        
        print(f"\nProcessing: {file_name}")
        
        # Parse the file
        trader_dict = parser.parse_html_file(file_path)
        
        if trader_dict:
            # Add file source info
            trader_dict["file_source"] = file_name
            
            all_traders_data.append(trader_dict)
            print(f"  ✅ Parsed successfully: {trader_dict['nickname']}")
            
        else:
            print(f"  ❌ Failed to parse: {file_name}")
    
    # Export all data
    if all_traders_data:
        # Individual files for each trader
        for trader in all_traders_data:
            filename = f"trader_{trader['portfolio_id']}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(trader, f, indent=2, ensure_ascii=False)
            print(f"✓ Exported: {filename}")
        
        # Combined file with all traders
        combined_data = {
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "total_traders": len(all_traders_data),
                "source_files": [trader["file_source"] for trader in all_traders_data]
            },
            "traders": all_traders_data
        }
        
        with open('all_traders.json', 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Export completed!")
        print(f"📄 Individual files: {len(all_traders_data)} trader JSON files")
        print(f"📄 Combined file: all_traders.json")
        print(f"📊 Total traders exported: {len(all_traders_data)}")
        
        # Print summary
        print(f"\n📋 Trader Summary:")
        for trader in all_traders_data:
            positions_count = len(trader['positions']) if isinstance(trader['positions'], dict) else ('Yes' if trader['positions'] else 'No')
            
            print(f"  • {trader['nickname']} (ID: {trader['portfolio_id']})")
            print(f"    ROI: {trader['roi']:.2f}% | AUM: ${trader['aum']:,.2f} | Positions: {positions_count}")
    
    else:
        print("No trader data was successfully parsed.")


if __name__ == "__main__":
    export_trader_data()