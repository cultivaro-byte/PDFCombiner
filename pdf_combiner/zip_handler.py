"""Safe extraction of ZIP archives.

Handles the failure modes required by the spec - encrypted, corrupted and
otherwise invalid archives - by raising a single, well-typed exception that the
orchestration layer can present to the user without crashing the batch.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

logger = logging.getLogger("pdf_combiner.zip_handler")


class ZipExtractionError(Exception):
    """Raised when a ZIP archive cannot be extracted.

    Wraps the underlying cause (bad zip file, encryption, OS error, ...) with a
    human-friendly message suitable for display in the UI.
    """


def _is_within_directory(directory: Path, target: Path) -> bool:
    """Return ``True`` if *target* resolves to a path inside *directory*.

    Used to defend against malicious archives containing ``../`` entries
    (a "zip slip" path-traversal attack).
    """

    directory = directory.resolve()
    try:
        target.resolve().relative_to(directory)
        return True
    except ValueError:
        return False


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Extract *zip_path* into *dest_dir* and return the extraction root.

    Parameters
    ----------
    zip_path:
        Path to the ``.zip`` archive on disk.
    dest_dir:
        Directory into which the archive's contents are written. It is created
        if it does not already exist.

    Raises
    ------
    ZipExtractionError
        If the archive is missing, not a valid ZIP, encrypted, corrupted, or
        contains unsafe (path-traversal) entries.
    """

    if not zip_path.is_file():
        raise ZipExtractionError(f"File not found: {zip_path.name}")

    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path) as archive:
            # ``testzip`` returns the name of the first bad file, or ``None``.
            bad_file = archive.testzip()
            if bad_file is not None:
                raise ZipExtractionError(
                    f"Archive '{zip_path.name}' is corrupted "
                    f"(bad entry: {bad_file})."
                )

            for member in archive.infolist():
                target_path = dest_dir / member.filename

                # Guard against zip-slip path traversal.
                if not _is_within_directory(dest_dir, target_path):
                    raise ZipExtractionError(
                        f"Archive '{zip_path.name}' contains an unsafe path: "
                        f"{member.filename}"
                    )

                try:
                    archive.extract(member, dest_dir)
                except RuntimeError as exc:
                    # zipfile raises RuntimeError("File is encrypted ...").
                    if "encrypted" in str(exc).lower():
                        raise ZipExtractionError(
                            f"Archive '{zip_path.name}' is password protected "
                            f"and cannot be processed."
                        ) from exc
                    raise ZipExtractionError(
                        f"Failed to extract '{member.filename}' from "
                        f"'{zip_path.name}': {exc}"
                    ) from exc

    except zipfile.BadZipFile as exc:
        raise ZipExtractionError(
            f"'{zip_path.name}' is not a valid ZIP archive."
        ) from exc
    except zipfile.LargeZipFile as exc:
        raise ZipExtractionError(
            f"'{zip_path.name}' requires ZIP64 support which is unavailable."
        ) from exc
    except ZipExtractionError:
        raise
    except OSError as exc:
        raise ZipExtractionError(
            f"I/O error while reading '{zip_path.name}': {exc}"
        ) from exc

    logger.info("Extracted '%s' into '%s'", zip_path.name, dest_dir)
    return dest_dir
