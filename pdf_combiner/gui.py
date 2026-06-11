"""PyQt6 main window.

Implements every UI requirement: drag-and-drop of ZIP files, a file picker, an
output-folder selector, a progress bar, live status messages and a Merge button.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import config
from .processor import BatchResult
from .worker import MergeWorker

logger = logging.getLogger("pdf_combiner.gui")


class DropListWidget(QListWidget):
    """A list widget that accepts ZIP files dropped onto it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.setToolTip("Drag ZIP files here, or use 'Add ZIP files...'")

    # -- Drag & drop handlers ------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths: list[str] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local.lower().endswith(".zip"):
                paths.append(local)
        if paths:
            # Delegate to the parent window so de-duplication stays in one place.
            window = self.window()
            if isinstance(window, MainWindow):
                window.add_zip_files(paths)
            event.acceptProposedAction()
        else:
            event.ignore()


class MainWindow(QWidget):
    """The application's single main window."""

    def __init__(self) -> None:
        super().__init__()
        self._worker: MergeWorker | None = None
        self._output_dir: Path = Path.home() / "Desktop"

        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.setMinimumSize(560, 460)
        self.setAcceptDrops(True)
        self._build_ui()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- ZIP file list ---------------------------------------------------
        layout.addWidget(QLabel("ZIP archives to process:"))
        self.file_list = DropListWidget()
        layout.addWidget(self.file_list, stretch=1)

        # --- File list buttons ----------------------------------------------
        list_buttons = QHBoxLayout()
        self.add_button = QPushButton("Add ZIP files...")
        self.add_button.clicked.connect(self._on_add_files)
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.clicked.connect(self._on_remove_selected)
        self.clear_button = QPushButton("Clear all")
        self.clear_button.clicked.connect(self._on_clear)
        list_buttons.addWidget(self.add_button)
        list_buttons.addWidget(self.remove_button)
        list_buttons.addWidget(self.clear_button)
        list_buttons.addStretch(1)
        layout.addLayout(list_buttons)

        # --- Output folder selector -----------------------------------------
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        self.output_edit = QLineEdit(str(self._output_dir))
        self.output_edit.setReadOnly(True)
        output_row.addWidget(self.output_edit, stretch=1)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_choose_output)
        output_row.addWidget(self.browse_button)
        layout.addLayout(output_row)

        # --- Progress bar ----------------------------------------------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # --- Status label ----------------------------------------------------
        self.status_label = QLabel("Ready.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # --- Merge / Cancel buttons -----------------------------------------
        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.merge_button = QPushButton("Merge")
        self.merge_button.setDefault(True)
        self.merge_button.clicked.connect(self._on_merge)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel)
        action_row.addWidget(self.merge_button)
        action_row.addWidget(self.cancel_button)
        layout.addLayout(action_row)

    # ----------------------------------------------------- public helpers --
    def add_zip_files(self, paths: list[str]) -> None:
        """Add ZIP paths to the list, skipping duplicates."""

        existing = {
            self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.file_list.count())
        }
        added = 0
        for raw in paths:
            resolved = str(Path(raw).resolve())
            if resolved in existing:
                continue
            item = QListWidgetItem(Path(resolved).name)
            item.setData(Qt.ItemDataRole.UserRole, resolved)
            item.setToolTip(resolved)
            self.file_list.addItem(item)
            existing.add(resolved)
            added += 1
        if added:
            self.status_label.setText(f"Added {added} file(s).")

    # ------------------------------------------------- window drag & drop --
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.toLocalFile().lower().endswith(".zip")
        ]
        if paths:
            self.add_zip_files(paths)
            event.acceptProposedAction()

    # -------------------------------------------------------- UI callbacks --
    def _on_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select ZIP archives", str(Path.home()), "ZIP archives (*.zip)"
        )
        if paths:
            self.add_zip_files(paths)

    def _on_remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def _on_clear(self) -> None:
        self.file_list.clear()
        self.status_label.setText("Cleared.")

    def _on_choose_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select output folder", str(self._output_dir)
        )
        if directory:
            self._output_dir = Path(directory)
            self.output_edit.setText(directory)

    def _collect_zip_paths(self) -> list[Path]:
        return [
            Path(self.file_list.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self.file_list.count())
        ]

    # ----------------------------------------------------- merge lifecycle --
    def _on_merge(self) -> None:
        zip_paths = self._collect_zip_paths()
        if not zip_paths:
            QMessageBox.warning(
                self, config.APP_NAME, "Please add at least one ZIP file."
            )
            return

        if not self._output_dir.exists():
            try:
                self._output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                QMessageBox.critical(
                    self,
                    config.APP_NAME,
                    f"Cannot create output folder:\n{exc}",
                )
                return

        self._set_processing(True)
        self.progress_bar.setValue(0)

        self._worker = MergeWorker(zip_paths, self._output_dir)
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.status.connect(self.status_label.setText)
        self._worker.finished_batch.connect(self._on_finished)
        self._worker.start()

    def _on_cancel(self) -> None:
        if self._worker is not None:
            self.status_label.setText("Cancelling after current archive...")
            self._worker.cancel()
            self.cancel_button.setEnabled(False)

    def _on_finished(self, result: BatchResult) -> None:
        self._set_processing(False)
        self.progress_bar.setValue(100)

        summary = (
            f"Done. {result.succeeded} succeeded, {result.failed} failed."
        )
        self.status_label.setText(summary)

        # Build a detailed report for the dialog.
        lines: list[str] = []
        for r in result.results:
            mark = "OK " if r.success else "ERR"
            lines.append(f"[{mark}] {r.zip_path.name}: {r.message}")
        detail = "\n".join(lines) if lines else "Nothing was processed."

        box = QMessageBox(self)
        box.setWindowTitle(config.APP_NAME)
        box.setText(summary)
        box.setDetailedText(detail)
        box.setIcon(
            QMessageBox.Icon.Information
            if result.failed == 0
            else QMessageBox.Icon.Warning
        )
        box.exec()

        self._worker = None

    def _set_processing(self, processing: bool) -> None:
        """Enable/disable controls while a batch is running."""

        self.merge_button.setEnabled(not processing)
        self.cancel_button.setEnabled(processing)
        self.add_button.setEnabled(not processing)
        self.remove_button.setEnabled(not processing)
        self.clear_button.setEnabled(not processing)
        self.browse_button.setEnabled(not processing)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Make sure a running worker is stopped cleanly on exit."""

        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)
        event.accept()
