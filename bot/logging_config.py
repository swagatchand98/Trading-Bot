"""
Logging configuration for the trading bot.

Sets up dual logging:
  - Console : INFO-level, concise format
  - File    : DEBUG-level, detailed format with timestamps, auto-rotated

Log files are stored in ``<project-root>/logs/`` and are automatically
rotated when they exceed 5 MB, keeping the last 5 backups.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

# Rotation settings
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_BACKUP_COUNT = 5              # keep 5 old rotated files


def setup_logging(log_level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure and return the application logger.

    Creates a ``logs/`` directory next to the package root and writes to
    a rotating log file (``trading_bot.log``).

    Parameters
    ----------
    log_level : int
        Minimum level for the *file* handler (console is always INFO).

    Returns
    -------
    logging.Logger
        Configured logger instance named ``trading_bot``.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(log_level)

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # --- File handler (detailed, auto-rotated) ---------------------------------
    log_file = LOG_DIR / "trading_bot.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    # --- Console handler (concise) ---------------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter("%(levelname)-8s | %(message)s")
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.debug("Logging initialised – file: %s", log_file)
    return logger
