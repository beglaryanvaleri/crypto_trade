# Liquidation Monitor

Monitor Binance Futures liquidation orders across all active perpetual futures symbols.

## Usage

### Basic monitoring (testnet, no data saving)
```bash
python liquidation_monitor
```

### Live trading mode with data saving
```bash
python liquidation_monitor --trade-mode live --save-data
```

### Data Storage

When `--save-data` is enabled, liquidation data is saved to:
- Directory: `data/liquidations/`
- Format: JSON Lines (`.jsonl`)
- Filename: `liquidations_{trade_mode}_{timestamp}.jsonl`

Each liquidation record contains:
```json
{
  "timestamp": 1234567890123,
  "datetime": "2024-01-01T12:00:00.123000",
  "symbol": "BTCUSDT",
  "side": "SELL",
  "quantity": 0.001,
  "price": 45000.0,
  "avg_price": 45100.0,
  "order_status": "FILLED",
  "order_type": "LIMIT",
  "time_in_force": "IOC"
}
```