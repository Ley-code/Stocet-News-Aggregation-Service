"""Logging configuration using loguru."""
import os
import sys
from loguru import logger
from .config import settings


def configure_logging():
    """Configure loguru logger with settings."""
    # Remove default handler
    logger.remove()
    
    # Add console handler with format
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    logger.info(f"Logging configured with level: {settings.log_level}")

