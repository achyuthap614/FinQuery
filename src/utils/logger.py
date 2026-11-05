"""Logging configuration for FinQuery application."""
import logging
import sys

def setup_logger(name: str = "finquery", level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a standardized logger with timestamp and level formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger

logger = setup_logger()
