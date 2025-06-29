#!/usr/bin/env python3
"""
Simple script to read and display information from a single Binance portfolio HTML file.
"""

import os
from binance_portfolio_parser import BinancePortfolioParser


def main():
    """Read and display portfolio information."""
    
    # Path to the portfolio data
    portfolio_dir = os.path.expanduser("~/Downloads/binance_portfolio")
    
    # Check if directory exists
    if not os.path.exists(portfolio_dir):
        print(f"Error: Directory {portfolio_dir} not found")
        print("Please ensure you have saved the HTML files in this location")
        return
    
    # List HTML files
    html_files = [f for f in os.listdir(portfolio_dir) if f.endswith('.html')]
    
    if not html_files:
        print(f"No HTML files found in {portfolio_dir}")
        return
    
    print(f"Found {len(html_files)} HTML files: {html_files}")
    
    # Initialize parser
    parser = BinancePortfolioParser()
    
    # Read all files
    for file_name in html_files:
        file_path = os.path.join(portfolio_dir, file_name)
        
        print(f"\nReading file: {file_name}")
        print("=" * 60)
        
        # Parse the file
        trader_data = parser.parse_html_file(file_path)
        
        if trader_data:
            # Display summary
            print(parser.get_summary(trader_data))
            
        else:
            print("Failed to parse the file")


if __name__ == "__main__":
    main()