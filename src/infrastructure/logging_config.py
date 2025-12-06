"""Structured logging configuration."""

import logging
import sys
from typing import Optional
from src.config import config


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Optional log level override (defaults to config.LOG_LEVEL)
    """
    level = log_level or config.LOG_LEVEL
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific loggers
    logging.getLogger("src").setLevel(numeric_level)

    # Reduce noise from third-party libraries
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
