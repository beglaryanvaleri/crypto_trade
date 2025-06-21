#!/usr/bin/env python3
"""
Main entry point for crypto_trade application.
"""
import asyncio
import sys
from src.utils.logger import get_logger, setup_logger


async def main():
    """Main application entry point."""
    # Setup logger with custom configuration if needed
    setup_logger(log_level='INFO', keep_days=7)  # Keep logs for 7 days
    
    # Get logger instance
    logger = get_logger('main')
    
    logger.info("Crypto Trade application started")
    logger.debug("Debug message - will appear in file but not console")
    
    try:
        # Application logic will go here
        logger.info("System initialized successfully")
        
        # Example of different log levels
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        
        # Placeholder for future functionality
        logger.info("Ready to start trading operations...")
        
    except Exception as e:
        logger.exception(f"Application error: {e}")
        return 1
    
    logger.info("Crypto Trade application stopped")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)