"""Application-wide configuration and constants.

All values that a deployer might reasonably want to tweak live here so that the
rest of the codebase stays free of magic strings/numbers.
"""

from __future__ import annotations

from typing import Final

#: Human readable application name (used for window title, log header, etc.).
APP_NAME: Final[str] = "PDF Combiner"

#: Application version. Kept in sync with ``pdf_combiner.__version__``.
APP_VERSION: Final[str] = "1.0.0"

#: Name of the error/activity log file written next to the executable.
LOG_FILENAME: Final[str] = "pdf_combiner.log"

# ---------------------------------------------------------------------------
# Special-PDF ordering
# ---------------------------------------------------------------------------
# Some PDFs must always be appended *after* the alphabetically sorted documents,
# in a fixed, deterministic order. List their file names (case-insensitive,
# matched on the base file name only) here, in the exact order they should
# appear at the end of the merged document.
#
# If a listed file is not present in a given archive it is simply skipped - the
# merge never fails because a special PDF is missing.
#
# Example:
#   SPECIAL_PDF_ORDER = (
#       "terms_and_conditions.pdf",
#       "signature_page.pdf",
#       "appendix.pdf",
#   )
#
# Leave the tuple empty to disable special ordering entirely (everything is then
# merged purely alphabetically).
SPECIAL_PDF_ORDER: Final[tuple[str, ...]] = (
    # "terms_and_conditions.pdf",
    # "signature_page.pdf",
)

#: File extension used to identify PDF documents (lower-cased comparison).
PDF_EXTENSION: Final[str] = ".pdf"

#: Prefix used for the per-run temporary extraction directory.
TEMP_DIR_PREFIX: Final[str] = "pdf_combiner_"
