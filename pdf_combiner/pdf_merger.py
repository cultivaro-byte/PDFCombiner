"""PDF ordering logic and merging.

Ordering rules (per specification):

1. Collect all PDFs from the archive.
2. Sort the *regular* PDFs alphabetically by file name.
3. Append the *special* PDFs at the end, in the exact order configured in
   :data:`pdf_combiner.config.SPECIAL_PDF_ORDER`.
4. If a special PDF is missing it is skipped.
5. The merge never fails because of a missing special PDF.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from . import config

logger = logging.getLogger("pdf_combiner.pdf_merger")


class PdfMergeError(Exception):
    """Raised when no PDF could be written to the output document."""


def order_pdfs(pdfs: list[Path]) -> list[Path]:
    """Return *pdfs* ordered according to the specification.

    Regular PDFs come first (alphabetical, case-insensitive by file name),
    followed by any configured special PDFs in their fixed order. Special PDFs
    that are absent from *pdfs* are skipped.
    """

    special_names_lower = [name.lower() for name in config.SPECIAL_PDF_ORDER]
    special_set = set(special_names_lower)

    # Partition into regular and special, keyed by lower-cased base name.
    regular: list[Path] = []
    special_lookup: dict[str, list[Path]] = {name: [] for name in special_names_lower}

    for pdf in pdfs:
        name_lower = pdf.name.lower()
        if name_lower in special_set:
            special_lookup[name_lower].append(pdf)
        else:
            regular.append(pdf)

    # 2. Sort regular PDFs alphabetically (case-insensitive) by file name.
    regular.sort(key=lambda p: p.name.lower())

    # 3./4. Append specials in configured order, skipping any that are missing.
    ordered: list[Path] = list(regular)
    for name_lower in special_names_lower:
        for pdf in special_lookup[name_lower]:
            ordered.append(pdf)

    return ordered


def merge_pdfs(ordered_pdfs: list[Path], output_path: Path) -> int:
    """Merge *ordered_pdfs* into a single PDF written to *output_path*.

    Individual unreadable/corrupt PDFs are logged and skipped rather than
    aborting the whole merge. Returns the number of source documents that were
    successfully appended.

    Raises
    ------
    PdfMergeError
        If, after attempting every input, not a single page could be written.
    """

    writer = PdfWriter()
    appended = 0

    for pdf in ordered_pdfs:
        try:
            reader = PdfReader(pdf)

            # Transparently handle empty-password encrypted PDFs; otherwise skip.
            if reader.is_encrypted:
                try:
                    if reader.decrypt("") == 0:  # 0 == decryption failed
                        logger.warning(
                            "Skipping password-protected PDF: %s", pdf.name
                        )
                        continue
                except (PdfReadError, NotImplementedError) as exc:
                    logger.warning(
                        "Skipping PDF with unsupported encryption '%s': %s",
                        pdf.name,
                        exc,
                    )
                    continue

            writer.append(reader)
            appended += 1
            logger.info("Appended '%s'", pdf.name)
        except (PdfReadError, OSError, ValueError) as exc:
            # Corrupt or otherwise unreadable file - skip and keep going.
            logger.warning("Skipping unreadable PDF '%s': %s", pdf.name, exc)

    if appended == 0:
        raise PdfMergeError("No valid PDF pages could be merged.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    writer.close()

    logger.info("Wrote merged PDF '%s' (%d source files)", output_path, appended)
    return appended
