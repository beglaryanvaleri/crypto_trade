import asyncio
from strategies.copy_trading.strategy import CopyTradingStrategy

async def main():
    strategy = CopyTradingStrategy()
    await strategy.run()

if __name__ == "__main__":
    asyncio.run(main())