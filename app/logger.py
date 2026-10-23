"""
Logging subsystem with rotating file handler and console handler.
Logs are placed in the portable data/logs directory.
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
from app.config import LOG_FILE, ensure_directories


_logger_initialized = False


def setup_logger(name: str = "CVModifier") -> logging.Logger:
    """Configures and returns the application logger."""
    global _logger_initialized
    logger = logging.getLogger(name)

    if _logger_initialized:
        return logger

    ensure_directories()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler (max 5MB, keep 5 backups)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not initialize log file: {e}")

    _logger_initialized = True
    return logger


logger = setup_logger()
