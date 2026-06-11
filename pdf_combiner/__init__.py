"""
PDF Combiner
============

A desktop application that extracts PDF files from ZIP archives and merges
them into a single PDF document per archive.

The package is split into focused, independently testable modules:

* :mod:`pdf_combiner.config`     - constants and the special-PDF ordering rules
* :mod:`pdf_combiner.logging_setup` - file + console logging configuration
* :mod:`pdf_combiner.zip_handler`  - safe ZIP extraction
* :mod:`pdf_combiner.pdf_locator`  - recursive PDF discovery
* :mod:`pdf_combiner.pdf_merger`   - ordering logic and merging
* :mod:`pdf_combiner.processor`    - end-to-end batch orchestration
* :mod:`pdf_combiner.worker`       - Qt worker thread wrapping the processor
* :mod:`pdf_combiner.gui`          - PyQt6 main window
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "1.0.0"
