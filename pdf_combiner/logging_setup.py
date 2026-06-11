"""Centralised logging configuration.

Errors and activity are written both to a rotating log file (placed next to the
executable / project root) and to the console for development.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import config


def get_log_path() -> Path:
    """Return the absolute path of the log file.

    When packaged with PyInstaller ``sys.frozen`` is set and ``sys.executable``
    points at the ``.exe``; we write the log next to it so a user can find it
    easily. In a normal interpreter run we fall back to the current working
    directory.
    """

    if getattr(sys, "frozen", False):  # running as a bundled executable
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path.cwd()
    return base_dir / config.LOG_FILENAME


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the application's root logger.

    Safe to call multiple times - handlers are only attached once.
    """

    logger = logging.getLogger("pdf_combiner")
    logger.setLevel(level)

    # Avoid duplicate handlers if called more than once (e.g. tests, re-import).
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler: keep the log bounded (1 MB x 3 backups).
    try:
        file_handler = RotatingFileHandler(
            get_log_path(),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # If the log file cannot be created (e.g. read-only location) we still
        # want the application to run - fall back to console-only logging.
        pass

    # Console handler (useful during development / when run from a terminal).
    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.propagate = False
    return logger
