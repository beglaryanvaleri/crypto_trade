# Copy Trading Strategy

A real-time copy trading strategy that monitors source trading accounts via WebSocket and replicates their trades in a main account with configurable position sizing and reverse trading options.

## 🚀 Quick Start

### 1. Configure Environment Variables

Edit `.env` file with your API credentials:

```env
# Main Account (where trades will be copied to)
MAIN_API_KEY=your_main_api_key
MAIN_API_SECRET=your_main_api_secret
MAIN_TESTNET_API_KEY=your_main_testnet_api_key
MAIN_TESTNET_API_SECRET=your_main_testnet_api_secret
MAIN_TRADING_MODE=testnet

# Source Account 1 (trades to copy from)
SOURCE_1_API_KEY=your_source_api_key
SOURCE_1_API_SECRET=your_source_api_secret
SOURCE_1_TESTNET_API_KEY=your_source_testnet_api_key
SOURCE_1_TESTNET_API_SECRET=your_source_testnet_api_secret
SOURCE_1_TRADING_MODE=testnet
```

### 2. Configure Trading Parameters

Edit `config.yaml` file:

```yaml
main_account:
  api_key: $MAIN_TESTNET_API_KEY
  api_secret: $MAIN_TESTNET_API_SECRET
  mode: $MAIN_TRADING_MODE

source_accounts:
  - name: "SourceTrader1"
    enabled: true
    api_key: $SOURCE_1_TESTNET_API_KEY
    api_secret: $SOURCE_1_TESTNET_API_SECRET
    mode: $SOURCE_1_TRADING_MODE
    coefficient: 1.0
    reverse_trades: false
```

### 3. Run the Strategy

```bash
# From project root
python src/strategies/copy_trading/main.py

# Or from strategy directory
cd src/strategies/copy_trading/
python main.py
```

## ✨ Features

### Real-time Monitoring
- **WebSocket Integration**: Listens to user data streams from all source accounts
- **Order Detection**: Detects FILLED orders immediately via `ORDER_TRADE_UPDATE` events
- **Main Account Monitoring**: Also monitors main account for confirmation

### Trade Copying
- **Market Orders**: Copies trades using market orders for immediate execution
- **Position Sizing**: Applies coefficient multipliers (e.g., 1.5x, 0.5x)
- **Reverse Trading**: Option to invert trades (BUY→SELL, SELL→BUY)
- **Precision Handling**: Automatically rounds quantities to valid lot sizes

### Configuration
- **Environment Variables**: Credentials stored in `.env` file
- **YAML Configuration**: Trading parameters in `config.yaml`
- **Multiple Sources**: Support for multiple source accounts simultaneously

## 🔄 How It Works

1. **Initialization**: Creates interfaces for main and source accounts
2. **WebSocket Connections**: Establishes user data streams for all accounts
3. **Trade Detection**: Monitors for `ORDER_TRADE_UPDATE` events with status `FILLED`
4. **Calculation**: Applies coefficient to original quantity
5. **Execution**: Places market order on main account
6. **Confirmation**: Logs execution details and broker responses

## ⚙️ Configuration Options

### Source Account Parameters
- `name`: Unique identifier for the source account
- `enabled`: Enable/disable this source (true/false)
- `coefficient`: Position size multiplier (1.0 = same size, 0.5 = half size, 2.0 = double size)
- `reverse_trades`: Invert trade direction (false = normal, true = opposite)

### Trading Modes
- `testnet`: Use Binance testnet for safe testing
- `live`: Use real Binance trading (use with caution)

## 🛡️ Safety Features

1. **Testnet Support**: Test everything on testnet first
2. **Quantity Rounding**: Automatically rounds to valid lot sizes
3. **Error Handling**: Comprehensive error logging
4. **Account Isolation**: Each source account runs independently

## 📁 File Structure

```
src/strategies/copy_trading/
├── main.py              # Entry point
├── strategy.py          # Core copy trading logic
├── config.py            # Configuration management
├── .env                 # API credentials
├── config.yaml          # Trading parameters
└── README.md           # This file
```

## 🔧 Technical Details

### WebSocket Message Handling
- Source accounts: Detects executions and triggers copy trades
- Main account: Logs all messages for confirmation and debugging

### Order Execution Flow
```python
# 1. Source executes: ETHUSDT BUY 0.1 @ $2000
# 2. Strategy calculates: 0.1 * 1.5 = 0.15
# 3. Strategy rounds: 0.15 -> 0.15 (valid lot size)
# 4. Strategy executes: main_interface.create_market_order('ETHUSDT', 'BUY', 0.15)
# 5. Broker confirms: Order filled
```

### Environment Variable Expansion
The strategy supports `$VARIABLE_NAME` syntax in `config.yaml` to reference environment variables from `.env` file.

## 🚨 Important Notes

1. **Start with Testnet**: Always test with testnet credentials first
2. **Monitor Closely**: Watch logs for any execution issues
3. **Small Coefficients**: Start with small position sizes (0.1-0.5)
4. **API Permissions**: Ensure API keys have futures trading permissions

## 🚀 Future Improvements

### Position Synchronization
- **Goal**: Implement position matching to ensure main account mirrors source accounts' positions
- **How**: Periodically check and compare positions between accounts, then adjust main account to match desired coefficient ratios
- **Benefit**: Handles cases where trades are missed or when starting with existing positions