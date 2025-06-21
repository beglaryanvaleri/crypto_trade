# Crypto Trading Framework

A Python framework providing common functionality for building cryptocurrency trading bots and implementing trading strategies with ease.

## Features

- **Common Interface**: Unified API for multiple exchanges (currently implementing Binance)
- **WebSocket Support**: Real-time market data and order execution monitoring
- **Trading Operations**: Market/limit orders, position management, portfolio tracking
- **Strategy Framework**: Ready-to-use structure for implementing trading strategies
- **Async/Await**: High-performance async operations for trading

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API credentials

# Run examples
python examples/binance_websocket.py
```

## Structure

- `src/exchanges/` - Exchange implementations (Binance Futures)
- `src/strategies/` - Trading strategy implementations
- `examples/` - Usage examples for different modules

## Examples

Check the `examples/` directory for:
- Binance Futures WebSocket data streaming
- Binance Futures Order execution and monitoring

## Contributing

Feel free to make suggestions or report issues. This project aims to provide a solid foundation for algorithmic trading development.

## License

MIT License
