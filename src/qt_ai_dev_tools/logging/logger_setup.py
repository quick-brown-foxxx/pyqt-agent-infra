"""Logging setup utilities.

Provides rotating file logging, colored stderr logging, and utilities for
configuring logger levels.

Key principle:
    File logging is always on — it's the durable record for post-mortem debugging.
    Stderr logging is for CLI verbose mode — it keeps stdout clean for CLI output
    (piping, JSON, structured data) while showing real-time diagnostic info.
    CLI tools should NOT use stdout logging — use non_log_stdout_output instead,
    so that stdout stays clean for user-facing output (help, prompts, results).

Typical usage patterns:
    - CLI tools: file logging + stderr logging for verbose mode (-v/-vv)
    - All modes: configure_logger_level() to suppress noisy third-party loggers

Usage:
    from qt_ai_dev_tools.logging import (
        setup_stderr_logging,
        setup_file_logging,
        configure_logger_level,
    )

    # File logging always on
    setup_file_logging(log_dir=Path("~/.local/state/qt-ai-dev-tools/logs"), app_name="qt-ai-dev-tools")

    # Stderr logging for verbose mode (keeps stdout clean for CLI output)
    setup_stderr_logging(level=logging.INFO)   # -v
    setup_stderr_logging(level=logging.DEBUG)  # -vv

    # Suppress noisy loggers
    configure_logger_level("httpx", logging.WARNING)

Stderr output format:
    <colored>2025-12-19 00:01:35 [INFO] module.name:</colored> <default>Log message text</default>

File output format:
    2025-12-19 00:01:35 [INFO] module.name: Log message text

Colors:
    - DEBUG: Cyan
    - INFO: Green
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Red on white background
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import colorlog


def setup_stderr_logging(level: int = logging.INFO) -> None:
    """Set up stderr logging with colored log prefix but uncolored messages.

    Adds a colored StreamHandler writing to stderr to the root logger. Use for
    CLI verbose mode (-v/-vv) — stderr keeps stdout clean for piping, JSON output,
    and structured CLI data. Log messages appear on stderr so they don't interfere
    with the primary CLI output stream.

    Args:
        level: Logging level to use
    """
    handler = colorlog.StreamHandler(sys.stderr)
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s] %(name)s:%(reset)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
            reset=True,
        )
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    # Set root level to the lowest of current and requested, so both
    # stderr and file handlers can filter independently
    if root_logger.level == logging.NOTSET or level < root_logger.level:
        root_logger.setLevel(level)


def setup_file_logging(
    log_dir: Path,
    app_name: str = "app",
    level: int = logging.DEBUG,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> None:
    """Set up rotating file logging.

    Adds a RotatingFileHandler to the root logger. File logs are always written
    (typically at DEBUG level) regardless of whether stderr logging is active.

    The log file is created at: <log_dir>/<app_name>.log

    Args:
        log_dir: Directory to store log files (created if missing)
        app_name: Name used for the log file (becomes <app_name>.log)
        level: Logging level for the file handler (default: DEBUG — capture everything)
        max_bytes: Max size per log file before rotation (default: 5 MB)
        backup_count: Number of rotated log files to keep (default: 3)
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{app_name}.log"

    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    # Set root level to the lowest of current and requested
    if root_logger.level == logging.NOTSET or level < root_logger.level:
        root_logger.setLevel(level)


def configure_logger_level(logger_name: str, level: int, propagate: bool = True) -> None:
    """Configure a specific logger's level and propagation.

    Args:
        logger_name: Name of the logger to configure
        level: Logging level to set
        propagate: Whether to propagate to parent loggers
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = propagate
