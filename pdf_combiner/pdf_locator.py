"""Recursive discovery of PDF files within an extracted archive."""

from __future__ import annotations

import logging
from pathlib import Path

from . import config

logger = logging.getLogger("pdf_combiner.pdf_locator")


def find_pdfs(root: Path) -> list[Path]:
    """Return every PDF file found under *root*, including in subfolders.

    The search is case-insensitive on the extension (``.pdf``/``.PDF``) and
    skips directories that merely *end* in ``.pdf``. The returned list is
    unsorted - ordering is the responsibility of :mod:`pdf_combiner.pdf_merger`.
    """

    pdfs: list[Path] = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() == config.PDF_EXTENSION
    ]

    logger.info("Found %d PDF(s) under '%s'", len(pdfs), root)
    return pdfs
