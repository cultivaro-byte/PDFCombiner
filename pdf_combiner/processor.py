"""End-to-end batch orchestration.

This module is deliberately free of any Qt dependency so it can be unit-tested
and reused headlessly. The GUI layer drives it through plain callbacks.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from . import config
from .pdf_locator import find_pdfs
from .pdf_merger import PdfMergeError, merge_pdfs, order_pdfs
from .zip_handler import ZipExtractionError, extract_zip

logger = logging.getLogger("pdf_combiner.processor")

# Callback signatures used to report progress back to the caller (e.g. the GUI).
#   ProgressCallback(percent: int)         - overall progress, 0..100
#   StatusCallback(message: str)           - human-readable current step
ProgressCallback = Callable[[int], None]
StatusCallback = Callable[[str], None]


@dataclass
class ArchiveResult:
    """Outcome of processing a single ZIP archive."""

    zip_path: Path
    success: bool
    output_path: Path | None = None
    merged_count: int = 0
    message: str = ""


@dataclass
class BatchResult:
    """Aggregate outcome of processing a batch of archives."""

    results: list[ArchiveResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.success)


def _noop(*_args: object, **_kwargs: object) -> None:
    """Default callback that does nothing."""


def process_archive(
    zip_path: Path,
    output_dir: Path,
    *,
    status: StatusCallback = _noop,
) -> ArchiveResult:
    """Process a single ZIP archive into one merged PDF.

    The merged file is named after the archive (``Application_123.zip`` ->
    ``Application_123.pdf``) and placed in *output_dir*. A dedicated temporary
    directory is created for extraction and always removed afterwards.
    """

    output_path = output_dir / f"{zip_path.stem}{config.PDF_EXTENSION}"
    temp_dir: Path | None = None

    try:
        # 1. Extract --------------------------------------------------------
        status(f"Extracting '{zip_path.name}'...")
        temp_dir = Path(tempfile.mkdtemp(prefix=config.TEMP_DIR_PREFIX))
        extract_zip(zip_path, temp_dir)

        # 2. Locate ---------------------------------------------------------
        status(f"Searching for PDFs in '{zip_path.name}'...")
        pdfs = find_pdfs(temp_dir)
        if not pdfs:
            message = f"No PDF files found in '{zip_path.name}'."
            logger.warning(message)
            return ArchiveResult(zip_path, success=False, message=message)

        # 3. Order + merge --------------------------------------------------
        status(f"Merging {len(pdfs)} PDF(s) from '{zip_path.name}'...")
        ordered = order_pdfs(pdfs)
        merged_count = merge_pdfs(ordered, output_path)

        message = (
            f"Created '{output_path.name}' from {merged_count} PDF(s)."
        )
        logger.info(message)
        return ArchiveResult(
            zip_path,
            success=True,
            output_path=output_path,
            merged_count=merged_count,
            message=message,
        )

    except ZipExtractionError as exc:
        logger.error("Extraction failed for '%s': %s", zip_path.name, exc)
        return ArchiveResult(zip_path, success=False, message=str(exc))
    except PdfMergeError as exc:
        logger.error("Merge failed for '%s': %s", zip_path.name, exc)
        return ArchiveResult(
            zip_path, success=False, message=f"{zip_path.name}: {exc}"
        )
    except Exception as exc:  # noqa: BLE001 - last-resort guard per archive
        # A single bad archive must never crash the whole batch.
        logger.exception("Unexpected error processing '%s'", zip_path.name)
        return ArchiveResult(
            zip_path,
            success=False,
            message=f"Unexpected error processing '{zip_path.name}': {exc}",
        )
    finally:
        # 4. Always clean up the temporary extraction directory.
        if temp_dir is not None and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug("Removed temporary directory '%s'", temp_dir)


def process_batch(
    zip_paths: Sequence[Path],
    output_dir: Path,
    *,
    progress: ProgressCallback = _noop,
    status: StatusCallback = _noop,
    should_cancel: Callable[[], bool] = lambda: False,
) -> BatchResult:
    """Process several archives, reporting progress as it goes.

    Parameters
    ----------
    zip_paths:
        Archives to process.
    output_dir:
        Destination directory for the merged PDFs.
    progress:
        Called with an integer 0..100 representing overall completion.
    status:
        Called with a short human-readable description of the current step.
    should_cancel:
        Polled between archives; if it returns ``True`` the batch stops early.
    """

    batch = BatchResult()
    total = len(zip_paths)
    if total == 0:
        return batch

    output_dir.mkdir(parents=True, exist_ok=True)
    progress(0)

    for index, zip_path in enumerate(zip_paths):
        if should_cancel():
            status("Cancelled.")
            logger.info("Batch cancelled by user after %d archive(s).", index)
            break

        result = process_archive(zip_path, output_dir, status=status)
        batch.results.append(result)

        # Report progress as whole archives completed.
        progress(int(round((index + 1) / total * 100)))

    return batch
