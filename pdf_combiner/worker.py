"""Qt worker thread that runs the batch processor off the UI thread.

Keeping the heavy lifting in a :class:`QThread` keeps the interface responsive
and lets the progress bar / status label update live.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PyQt6.QtCore import QThread, pyqtSignal

from .processor import BatchResult, process_batch


class MergeWorker(QThread):
    """Runs :func:`pdf_combiner.processor.process_batch` in a background thread.

    Signals
    -------
    progress(int)
        Overall completion percentage (0..100).
    status(str)
        Human-readable description of the current processing step.
    finished_batch(object)
        Emitted once with the :class:`BatchResult` when processing completes.
    """

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished_batch = pyqtSignal(object)

    def __init__(
        self,
        zip_paths: Sequence[Path],
        output_dir: Path,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._zip_paths = list(zip_paths)
        self._output_dir = output_dir
        self._cancel_requested = False

    def cancel(self) -> None:
        """Request cooperative cancellation after the current archive."""

        self._cancel_requested = True

    def run(self) -> None:  # noqa: D401 - QThread entry point
        """Execute the batch, forwarding progress through Qt signals."""

        result: BatchResult = process_batch(
            self._zip_paths,
            self._output_dir,
            progress=self.progress.emit,
            status=self.status.emit,
            should_cancel=lambda: self._cancel_requested,
        )
        self.finished_batch.emit(result)
