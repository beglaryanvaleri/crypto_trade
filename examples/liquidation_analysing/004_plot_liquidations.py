"""
Step 4: Plot liquidation charts for visual analysis.
"""
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import shutil
import os
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
FILTERED_LIQUIDATIONS_FILE = 'filtered_liquidations.csv'
CANDLES_DIR = 'candles'
CHARTS_DIR = 'charts'
HOURS_BEFORE = 6        # Hours to show before liquidation
HOURS_AFTER = 18        # Hours to show after liquidation
MAX_CHARTS_PER_FILE = 20 # Maximum number of charts per HTML file
MAX_TOTAL_CHARTS = 500   # Maximum total charts to generate


def setup_charts_directory():
    """Remove and recreate charts directory."""
    if os.path.exists(CHARTS_DIR):
        shutil.rmtree(CHARTS_DIR)
    os.makedirs(CHARTS_DIR)
    print(f"Created fresh charts directory: {CHARTS_DIR}")


def load_candle_data(symbol):
    """Load candle data for a symbol."""
    file_path = Path(CANDLES_DIR) / f"{symbol}_1m.csv"
    if not file_path.exists():
        return None
    
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['volume_usdt'] = df['volume'] * df['close']
    return df


def create_html_file(chart_divs, liquidations_batch, file_num, total_files, start_time, end_time):
    """Create HTML file with charts for a batch of liquidations."""
    charts_count = len(chart_divs)
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Liquidation Analysis - Page {file_num}</title>
    <meta charset="utf-8">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{ 
            font-family: Arial, sans-serif; 
            background-color: #f5f5f5;
            overflow-x: hidden;
        }}
        
        .container {{
            display: flex;
            height: 100vh;
        }}
        
        .sidebar {{
            width: 350px;
            background: #2c3e50;
            color: white;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 2px 0 5px rgba(0,0,0,0.1);
        }}
        
        .sidebar-header {{
            padding: 20px;
            background: #34495e;
            border-bottom: 1px solid #4a5f7a;
        }}
        
        .sidebar-header h1 {{
            color: #ecf0f1;
            font-size: 18px;
            margin-bottom: 10px;
        }}
        
        .sidebar-header .stats {{
            font-size: 13px;
            color: #bdc3c7;
            line-height: 1.4;
        }}
        
        .page-nav {{
            padding: 15px 20px;
            background: #1a252f;
            border-bottom: 1px solid #34495e;
        }}
        
        .page-nav h3 {{
            color: #f39c12;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        
        .page-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }}
        
        .page-link {{
            padding: 5px 10px;
            background: #34495e;
            color: #ecf0f1;
            text-decoration: none;
            border-radius: 3px;
            font-size: 12px;
            transition: background 0.3s;
        }}
        
        .page-link:hover {{
            background: #3498db;
        }}
        
        .page-link.current {{
            background: #e74c3c;
        }}
        
        .nav-list {{
            list-style: none;
            padding: 0;
        }}
        
        .nav-item {{
            border-bottom: 1px solid #34495e;
        }}
        
        .nav-link {{
            display: block;
            padding: 15px 20px;
            color: #ecf0f1;
            text-decoration: none;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .nav-link:hover {{
            background: #3498db;
            color: white;
        }}
        
        .nav-link.active {{
            background: #e74c3c;
            color: white;
            border-left: 4px solid #c0392b;
        }}
        
        .nav-symbol {{
            font-weight: bold;
            font-size: 15px;
            display: block;
        }}
        
        .nav-details {{
            font-size: 11px;
            color: #bdc3c7;
            margin-top: 5px;
            line-height: 1.3;
        }}
        
        .nav-amount {{
            color: #f39c12;
            font-weight: bold;
        }}
        
        .main-content {{
            margin-left: 350px;
            flex: 1;
            height: 100vh;
            overflow-y: auto;
            padding: 20px;
        }}
        
        .content-header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .content-header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        
        .chart-container {{ 
            background: white;
            margin: 20px 0; 
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            scroll-margin-top: 20px;
        }}
        
        .chart-header {{
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        
        .chart-title {{
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin: 0;
        }}
        
        .chart-details {{
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }}
        
        .back-to-top {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            cursor: pointer;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            z-index: 1001;
        }}
        
        .back-to-top:hover {{
            background: #2980b9;
        }}
        
        /* Custom scrollbar for sidebar */
        .sidebar::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .sidebar::-webkit-scrollbar-track {{
            background: #34495e;
        }}
        
        .sidebar::-webkit-scrollbar-thumb {{
            background: #7f8c8d;
            border-radius: 3px;
        }}
        
        .sidebar::-webkit-scrollbar-thumb:hover {{
            background: #95a5a6;
        }}
    </style>
    
    <script>
        let currentActive = null;
        
        function scrollToChart(chartId, navElement) {{
            // Remove active class from previous item
            if (currentActive) {{
                currentActive.classList.remove('active');
            }}
            
            // Add active class to clicked item
            navElement.classList.add('active');
            currentActive = navElement;
            
            // Scroll to chart
            const chartElement = document.getElementById(chartId);
            if (chartElement) {{
                chartElement.scrollIntoView({{
                    behavior: 'smooth',
                    block: 'start'
                }});
            }}
        }}
        
        function observeCharts() {{
            const options = {{
                root: null,
                rootMargin: '-20% 0px -70% 0px',
                threshold: 0.1
            }};
            
            const observer = new IntersectionObserver((entries) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        const chartId = entry.target.id;
                        const navElement = document.querySelector(`[onclick*="${{chartId}}"]`);
                        if (navElement && navElement !== currentActive) {{
                            if (currentActive) {{
                                currentActive.classList.remove('active');
                            }}
                            navElement.classList.add('active');
                            currentActive = navElement;
                        }}
                    }}
                }});
            }}, options);
            
            // Observe all chart containers
            document.querySelectorAll('.chart-container').forEach(chart => {{
                observer.observe(chart);
            }});
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            observeCharts();
            
            // Activate first item by default
            const firstNav = document.querySelector('.nav-link');
            if (firstNav) {{
                firstNav.classList.add('active');
                currentActive = firstNav;
            }}
        }});
    </script>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="sidebar-header">
                <h1>🔥 Liquidation Dashboard</h1>
                <div class="stats">
                    <div>Page {file_num} of {total_files}</div>
                    <div>Charts: {charts_count} | Range: ±{HOURS_BEFORE}/{HOURS_AFTER}h</div>
                    <div>Period: {start_time} - {end_time}</div>
                </div>
            </div>
            
            <div class="page-nav">
                <h3>📄 Pages</h3>
                <div class="page-links">
"""
    
    # Add page navigation links
    for i in range(1, total_files + 1):
        if i == file_num:
            html_content += f'                    <span class="page-link current">Page {i}</span>\n'
        else:
            html_content += f'                    <a href="liquidations_page_{i}.html" class="page-link">Page {i}</a>\n'
    
    html_content += """
                </div>
            </div>
            
            <ul class="nav-list">
"""
    
    # Add navigation links for this page
    for idx, (_, liquidation) in enumerate(liquidations_batch.iterrows()):
        symbol = liquidation['symbol']
        side = liquidation['side']
        usd_amount = liquidation['usd_amount']
        liq_datetime = pd.to_datetime(liquidation['timestamp'], unit='ms')
        vol_ratio = liquidation['volume_ratio']
        candle_ratio = liquidation['candle_ratio']
        volatility = liquidation['volatility']
        
        html_content += f"""
                <li class="nav-item">
                    <div class="nav-link" onclick="scrollToChart('chart_{idx}', this)">
                        <span class="nav-symbol">{symbol} {side}</span>
                        <div class="nav-details">
                            <span class="nav-amount">${usd_amount:,.0f}</span><br>
                            {liq_datetime.strftime('%m-%d %H:%M')} | Vol: {vol_ratio:.1f}x<br>
                            Candle: {candle_ratio:.1f}x | Vol: {volatility:.1%}
                        </div>
                    </div>
                </li>
"""
    
    html_content += """
            </ul>
        </div>
        
        <div class="main-content">
            <div class="content-header">
                <h1>📊 Liquidation Analysis</h1>
                <p>Interactive charts showing price and volume data around major liquidation events</p>
            </div>
"""
    
    # Add all chart divs for this page
    for idx, (chart_div, (_, liquidation)) in enumerate(zip(chart_divs, liquidations_batch.iterrows())):
        symbol = liquidation['symbol']
        side = liquidation['side']
        usd_amount = liquidation['usd_amount']
        liq_datetime = pd.to_datetime(liquidation['timestamp'], unit='ms')
        vol_ratio = liquidation['volume_ratio']
        candle_ratio = liquidation['candle_ratio']
        volatility = liquidation['volatility']
        
        html_content += f"""
    <div class="chart-container" id="chart_{idx}">
        <div class="chart-header">
            <h3 class="chart-title">#{idx+1} - {symbol} {side} Liquidation - ${usd_amount:,.0f}</h3>
            <div class="chart-details">
                🕐 {liq_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')} | 
                📊 Volume Ratio: {vol_ratio:.1f}x | 
                🕯️ Candle Ratio: {candle_ratio:.1f}x | 
                📈 Volatility: {volatility:.1%}
            </div>
        </div>
        {chart_div}
    </div>
"""
    
    html_content += """
            
            <div style="text-align: center; margin-top: 50px; padding: 20px; color: #666; font-size: 14px;">
                <p>Generated by Liquidation Analysis Tool</p>
            </div>
        </div>
        
        <button class="back-to-top" onclick="document.querySelector('.main-content').scrollTo({top: 0, behavior: 'smooth'})" title="Back to Top">
            ↑
        </button>
    </div>
    
</body>
</html>
"""
    
    return html_content


def create_liquidation_chart(liquidation_row, candles_df):
    """Create a chart for a single liquidation."""
    liq_timestamp = liquidation_row['timestamp']
    # Convert timestamp to datetime properly
    if isinstance(liq_timestamp, str):
        liq_datetime = pd.to_datetime(liquidation_row['datetime'])
    else:
        liq_datetime = pd.to_datetime(liq_timestamp, unit='ms')
    
    # Define time window
    start_time = liq_datetime - timedelta(hours=HOURS_BEFORE)
    end_time = liq_datetime + timedelta(hours=HOURS_AFTER)
    
    # Filter candles to time window
    chart_candles = candles_df[
        (candles_df['datetime'] >= start_time) & 
        (candles_df['datetime'] <= end_time)
    ].copy()
    
    if len(chart_candles) == 0:
        return None
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Price & Volume', 'Volume (USDT)'),
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        shared_xaxes=True
    )
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=chart_candles['datetime'],
            open=chart_candles['open'],
            high=chart_candles['high'],
            low=chart_candles['low'],
            close=chart_candles['close'],
            name='Price',
            increasing_line_color='green',
            decreasing_line_color='red'
        ),
        row=1, col=1
    )
    
    # Add liquidation marker
    liq_price = liquidation_row['price_at_liquidation']
    fig.add_trace(
        go.Scatter(
            x=[liq_datetime],
            y=[liq_price],
            mode='markers',
            marker=dict(
                size=15,
                color='yellow',
                symbol='star',
                line=dict(width=2, color='black')
            ),
            name=f'Liquidation ${liquidation_row["usd_amount"]:,.0f}',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Add volume bars
    fig.add_trace(
        go.Bar(
            x=chart_candles['datetime'],
            y=chart_candles['volume_usdt'],
            name='Volume (USDT)',
            marker_color='blue',
            opacity=0.6
        ),
        row=2, col=1
    )
    
    # Highlight liquidation volume
    # Find closest candle to liquidation time
    time_diffs = abs(chart_candles['datetime'] - liq_datetime)
    closest_idx = time_diffs.idxmin()
    liq_candle = chart_candles.loc[[closest_idx]]
    
    if len(liq_candle) > 0:
        fig.add_trace(
            go.Bar(
                x=[liq_candle.iloc[0]['datetime']],
                y=[liq_candle.iloc[0]['volume_usdt']],
                name='Liquidation Candle Volume',
                marker_color='red',
                opacity=0.8
            ),
            row=2, col=1
        )
    
    # Add vertical line at liquidation time using add_shape instead
    for row_num in range(1, 3):  # Add line to both subplots
        fig.add_shape(
            type="line",
            x0=liq_datetime, x1=liq_datetime,
            y0=0, y1=1,
            xref=f"x{row_num if row_num > 1 else ''}",
            yref=f"y{row_num if row_num > 1 else ''} domain",
            line=dict(color="red", width=2, dash="dash"),
            row=row_num, col=1
        )
    
    # Update layout
    symbol = liquidation_row['symbol']
    side = liquidation_row['side']
    usd_amount = liquidation_row['usd_amount']
    vol_ratio = liquidation_row['volume_ratio']
    candle_ratio = liquidation_row['candle_ratio']
    volatility = liquidation_row['volatility']
    
    title = (f"{symbol} {side} Liquidation - ${usd_amount:,.0f}<br>"
             f"Vol Ratio: {vol_ratio:.1f}x | Candle Ratio: {candle_ratio:.1f}x | "
             f"Volatility: {volatility:.1%} | {liq_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    fig.update_layout(
        title=title,
        title_font_size=14,
        height=800,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        template='plotly_white'
    )
    
    # Update axes
    fig.update_xaxes(title_text="Time (UTC)", row=2, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume (USDT)", row=2, col=1)
    
    return fig


def main():
    # Setup directory
    setup_charts_directory()
    
    # Load filtered liquidations
    if not os.path.exists(FILTERED_LIQUIDATIONS_FILE):
        print(f"Error: {FILTERED_LIQUIDATIONS_FILE} not found. Run 003_analyze_liquidations.py first.")
        return
    
    liquidations_df = pd.read_csv(FILTERED_LIQUIDATIONS_FILE)
    # Ensure timestamp is integer
    liquidations_df['timestamp'] = liquidations_df['timestamp'].astype('int64')
    print(f"Loaded {len(liquidations_df)} filtered liquidations")
    
    # Sort by timestamp (chronological order) and limit total
    liquidations_df = liquidations_df.sort_values('timestamp', ascending=True)
    liquidations_to_plot = liquidations_df.head(MAX_TOTAL_CHARTS)
    
    # Calculate number of files needed
    total_liquidations = len(liquidations_to_plot)
    total_files = (total_liquidations + MAX_CHARTS_PER_FILE - 1) // MAX_CHARTS_PER_FILE
    
    print(f"Creating {total_files} files with up to {MAX_CHARTS_PER_FILE} charts each...")
    print(f"Total liquidations to process: {total_liquidations}")
    
    # Get time range for header info
    start_time = pd.to_datetime(liquidations_to_plot.iloc[0]['timestamp'], unit='ms').strftime('%m-%d %H:%M')
    end_time = pd.to_datetime(liquidations_to_plot.iloc[-1]['timestamp'], unit='ms').strftime('%m-%d %H:%M')
    
    files_created = []
    total_charts_created = 0
    
    # Process each batch of liquidations
    for file_num in range(1, total_files + 1):
        start_idx = (file_num - 1) * MAX_CHARTS_PER_FILE
        end_idx = min(start_idx + MAX_CHARTS_PER_FILE, total_liquidations)
        batch = liquidations_to_plot.iloc[start_idx:end_idx]
        
        print(f"\n📄 Creating Page {file_num}/{total_files} ({len(batch)} liquidations)...")
        
        # Create charts for this batch
        chart_divs = []
        charts_created = 0
        
        for idx, (_, liquidation) in enumerate(batch.iterrows()):
            symbol = liquidation['symbol']
            timestamp = liquidation['timestamp']
            
            print(f"  [{idx+1}/{len(batch)}] Creating chart for {symbol} liquidation...")
            
            # Load candle data
            candles = load_candle_data(symbol)
            if candles is None:
                print(f"    ✗ No candle data for {symbol}")
                continue
            
            try:
                # Create chart
                fig = create_liquidation_chart(liquidation, candles)
                if fig is None:
                    print(f"    ✗ Not enough data for chart")
                    continue
                
                # Convert chart to HTML div
                chart_html = fig.to_html(
                    include_plotlyjs='cdn',  # Include plotly.js from CDN
                    div_id=f"chart_{idx}",
                    config={'displayModeBar': True, 'toImageButtonOptions': {'width': 1200, 'height': 800}}
                )
                
                # Extract just the div part
                start_div = chart_html.find('<div')
                end_div = chart_html.rfind('</div>') + 6
                chart_div = chart_html[start_div:end_div]
                
                chart_divs.append(chart_div)
                charts_created += 1
                total_charts_created += 1
                print(f"    ✓ Chart created")
                
            except Exception as e:
                import traceback
                print(f"    ✗ Error creating chart: {e}")
                traceback.print_exc()
                continue
        
        if charts_created > 0:
            # Create HTML content for this page
            html_content = create_html_file(
                chart_divs, 
                batch.head(charts_created), 
                file_num, 
                total_files, 
                start_time, 
                end_time
            )
            
            # Save file
            filename = f"liquidations_page_{file_num}.html"
            output_path = Path(CHARTS_DIR) / filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            files_created.append(filename)
            print(f"  ✅ Saved: {filename} ({charts_created} charts)")
        else:
            print(f"  ⚠️ No charts created for page {file_num}")
    
    # Create index file with links to all pages
    if files_created:
        index_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Liquidation Analysis - Index</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        .stats {{
            color: #666;
            font-size: 16px;
            line-height: 1.6;
        }}
        .pages-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .page-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .page-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }}
        .page-title {{
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .page-link {{
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            margin-top: 15px;
            transition: background 0.3s;
        }}
        .page-link:hover {{
            background: #2980b9;
        }}
        .page-stats {{
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 Liquidation Analysis Dashboard</h1>
        <div class="stats">
            <div><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
            <div><strong>Total Pages:</strong> {len(files_created)} | <strong>Total Charts:</strong> {total_charts_created}</div>
            <div><strong>Time Range:</strong> {start_time} - {end_time} | <strong>Chart Range:</strong> ±{HOURS_BEFORE}/{HOURS_AFTER}h</div>
        </div>
    </div>
    
    <div class="pages-grid">
"""
        
        # Add page cards
        for i, filename in enumerate(files_created, 1):
            # Calculate charts in this page
            start_idx = (i - 1) * MAX_CHARTS_PER_FILE
            end_idx = min(start_idx + MAX_CHARTS_PER_FILE, total_liquidations)
            page_charts = end_idx - start_idx
            
            # Get time range for this page
            page_batch = liquidations_to_plot.iloc[start_idx:end_idx]
            page_start = pd.to_datetime(page_batch.iloc[0]['timestamp'], unit='ms').strftime('%m-%d %H:%M')
            page_end = pd.to_datetime(page_batch.iloc[-1]['timestamp'], unit='ms').strftime('%m-%d %H:%M')
            
            index_content += f"""
        <div class="page-card">
            <div class="page-title">📊 Page {i}</div>
            <div class="page-stats">
                <div><strong>Charts:</strong> {page_charts}</div>
                <div><strong>Time Range:</strong> {page_start} - {page_end}</div>
            </div>
            <a href="{filename}" class="page-link">View Charts →</a>
        </div>
"""
        
        index_content += f"""
    </div>
    
    <div class="footer">
        <p>Generated by Liquidation Analysis Tool</p>
        <p>Charts are ordered chronologically by liquidation timestamp</p>
    </div>
</body>
</html>
"""
        
        # Save index file
        index_path = Path(CHARTS_DIR) / 'index.html'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"\n{'='*80}")
        print(f"✅ Created {len(files_created)} HTML files with {total_charts_created} total charts")
        print(f"📄 Index file: {index_path}")
        print(f"📄 Page files: {', '.join(files_created)}")
        print(f"🌐 Open index.html in browser to navigate all pages")
        print(f"📅 Charts ordered chronologically from {start_time} to {end_time}")
    else:
        print("No files were created.")


if __name__ == "__main__":
    main()