"""Application entry point.

Run with::

    python main.py

or launch the packaged ``PDFCombiner.exe`` produced by PyInstaller.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from pdf_combiner import config
from pdf_combiner.gui import MainWindow
from pdf_combiner.logging_setup import configure_logging


def main() -> int:
    """Configure logging, start the Qt event loop and return the exit code."""

    logger = configure_logging()
    logger.info("Starting %s v%s", config.APP_NAME, config.APP_VERSION)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)

    window = MainWindow()
    window.show()

    exit_code = app.exec()
    logger.info("Exiting with code %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
