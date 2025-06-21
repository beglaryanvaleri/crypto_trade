"""
Logger module with daily rotation at midnight.
"""
import os
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


class MidnightRotatingFileHandler(TimedRotatingFileHandler):
    """Custom handler that rotates log files at midnight with date in filename."""
    
    def __init__(self, log_dir: str, log_name: str, backupCount: int = 30, **kwargs):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.base_name = log_name
        
        # Initial filename with today's date
        today = datetime.now().strftime('%Y-%m-%d')
        filename = self.log_dir / f"{self.base_name}_{today}.log"
        
        super().__init__(
            filename=str(filename),
            when='midnight',
            interval=1,
            backupCount=backupCount,
            **kwargs
        )
        
    def doRollover(self):
        """Override to create new log file with date in name."""
        # Close current file
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # Generate new filename with tomorrow's date
        new_date = datetime.now().strftime('%Y-%m-%d')
        self.baseFilename = str(self.log_dir / f"{self.base_name}_{new_date}.log")
        
        # Open new file
        self.stream = self._open()
        
        # Clean up old logs (older than backupCount days)
        self._cleanup_old_logs()
    
    def _cleanup_old_logs(self):
        """Remove log files older than backupCount days."""
        if self.backupCount <= 0:
            return
            
        for log_file in self.log_dir.glob(f"{self.base_name}_*.log"):
            try:
                # Extract date from filename
                date_str = log_file.stem.split('_')[-1]
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Check if older than backupCount days
                days_old = (datetime.now() - file_date).days
                if days_old > self.backupCount:
                    log_file.unlink()
            except (ValueError, IndexError):
                # Skip files that don't match expected format
                continue


def setup_logger(
    name: str = 'crypto_trade',
    log_level: str = 'INFO',
    log_dir: str = 'logs',
    keep_days: int = 30
) -> logging.Logger:
    """
    Set up logger with console and file handlers.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        keep_days: Number of days to keep log files (default: 30)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler - simple format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler - detailed format, rotates at midnight
    file_handler = MidnightRotatingFileHandler(
        log_dir=log_dir,
        log_name='app',
        encoding='utf-8',
        backupCount=keep_days
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance. If name is provided, creates a child logger.
    
    Args:
        name: Optional name for child logger
        
    Returns:
        Logger instance
    """
    base_logger = logging.getLogger('crypto_trade')
    
    if name:
        return base_logger.getChild(name)
    return base_logger


# Create default logger instance
logger = setup_logger()