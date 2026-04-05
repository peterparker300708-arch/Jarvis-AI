"""Logging utility with colored console output and file rotation."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
COLORS = {
    "DEBUG": "\033[36m",      # Cyan
    "INFO": "\033[32m",       # Green
    "WARNING": "\033[33m",    # Yellow
    "ERROR": "\033[31m",      # Red
    "CRITICAL": "\033[35m",   # Magenta
}

_loggers: dict = {}


class ColoredFormatter(logging.Formatter):
    """Formatter that adds ANSI color codes to log level names."""

    def __init__(self, fmt: str, datefmt: str | None = None):
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        color = COLORS.get(record.levelname, RESET)
        record.levelname = f"{color}{BOLD}{record.levelname:<8}{RESET}"
        record.name = f"\033[34m{record.name}{RESET}"
        return super().format(record)


class PlainFormatter(logging.Formatter):
    """Plain formatter for file output without ANSI codes."""
    pass


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Return a configured logger with console (colored) and file (rotating) handlers.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.
        level: Minimum logging level. Defaults to DEBUG.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        _add_console_handler(logger)
        _add_file_handler(logger, name)

    _loggers[name] = logger
    return logger


def _add_console_handler(logger: logging.Logger) -> None:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    use_color = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%H:%M:%S"
    formatter = ColoredFormatter(fmt, datefmt) if use_color else PlainFormatter(fmt, datefmt)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def _add_file_handler(logger: logging.Logger, name: str) -> None:
    safe_name = name.replace(".", "_").replace("/", "_")
    log_file = os.path.join(LOG_DIR, f"{safe_name}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    file_handler.setFormatter(PlainFormatter(fmt))
    logger.addHandler(file_handler)


def set_global_level(level: int) -> None:
    """Change the level on every logger created by :func:`get_logger`."""
    for lg in _loggers.values():
        lg.setLevel(level)
        for handler in lg.handlers:
            handler.setLevel(level)
