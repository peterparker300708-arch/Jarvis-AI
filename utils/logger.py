"""
Logging setup for Jarvis AI.
"""

import os
import logging
import logging.handlers
from typing import Optional


def setup_logger(config=None, log_level: Optional[str] = None, log_file: Optional[str] = None):
    """Configure application-wide logging."""

    level_str = log_level or (config.get("app.log_level", "INFO") if config else "INFO")
    level = getattr(logging, level_str.upper(), logging.INFO)

    file_path = log_file or (config.get("app.log_file", "logs/jarvis.log") if config else "logs/jarvis.log")

    # Ensure log directory exists
    log_dir = os.path.dirname(file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # File handler (rotating)
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        root_logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        logging.getLogger(__name__).warning(f"Could not open log file {file_path}: {e}")

    # Reduce noise from third-party libraries
    for noisy in ("urllib3", "selenium", "scrapy", "asyncio", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return root_logger
