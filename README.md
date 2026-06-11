# PDF Combiner

A Windows desktop application that extracts PDF files from ZIP archives and
merges them into a single PDF per archive. Ships as a standalone `.exe` — no
Python installation required on the target machine.

## Features

- **Drag-and-drop** ZIP files onto the window, or pick them with a file dialog.
- **Batch processing** — drop in many archives at once.
- **Recursive PDF discovery** — finds PDFs in any subfolder of the archive.
- **Deterministic ordering** — regular PDFs alphabetical, configurable
  "special" PDFs appended at the end in a fixed order (missing ones skipped).
- **Progress bar + live status** during extraction and merging.
- **Output folder selector**.
- **Robust error handling** — encrypted / corrupted / invalid ZIPs and
  unreadable PDFs are reported, never crash the batch.
- **Automatic temp cleanup** and an error/activity **log file**.

## Output naming

Each archive yields one merged PDF named after the ZIP:

| Input                 | Output               |
|-----------------------|----------------------|
| `Application_123.zip` | `Application_123.pdf`|

## Project layout

```
PDFCombiner/
├── main.py                  # entry point (starts the Qt app)
├── pdf_combiner/
│   ├── config.py            # constants + SPECIAL_PDF_ORDER
│   ├── logging_setup.py     # file + console logging
│   ├── zip_handler.py       # safe ZIP extraction (zip-slip / encryption guards)
│   ├── pdf_locator.py       # recursive PDF discovery
│   ├── pdf_merger.py        # ordering rules + pypdf merge
│   ├── processor.py         # Qt-free batch orchestration (+ temp cleanup)
│   ├── worker.py            # QThread wrapper (keeps UI responsive)
│   └── gui.py               # PyQt6 main window
├── tests/test_core.py       # core logic tests (no Qt needed)
├── requirements.txt
├── PDFCombiner.spec         # PyInstaller build spec
└── build_windows.bat        # one-click Windows build
```

## Configuring the "special" PDF order

Open `pdf_combiner/config.py` and edit `SPECIAL_PDF_ORDER`:

```python
SPECIAL_PDF_ORDER = (
    "terms_and_conditions.pdf",
    "signature_page.pdf",
)
```

These file names (matched case-insensitively on the base name) are always
appended **after** the alphabetically-sorted documents, in exactly this order.
Any that are absent from a given archive are simply skipped. Leave the tuple
empty for pure alphabetical merging.

## Run from source

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Run the tests

The core logic has no Qt dependency, so tests run anywhere:

```bash
pip install pypdf pytest
pytest
```

## Build the standalone .exe (on Windows)

> PyInstaller produces an executable for the OS it runs on. To get a Windows
> `.exe`, run the build **on Windows** (a VM or CI runner is fine).

**Just double-click `build_windows.bat`.** It is fully self-contained:

- The only prerequisite is Python itself (needed to *build* the exe, not to
  *run* it). If it's missing the script tells you where to get it.
- It auto-detects Python (`py`, `python`, or `python3`), creates an isolated
  `.venv`, and installs PyQt6 / pypdf / PyInstaller **into that venv only** —
  nothing is installed system-wide.
- The finished **`PDFCombiner.exe` is placed directly on your Desktop**.
- The window stays open at the end so you can read the result.

That single `PDFCombiner.exe` can be copied to any Windows PC and run with no
Python installed there.

To build manually instead:

```bat
pyinstaller --clean --noconfirm --distpath "%USERPROFILE%\Desktop" PDFCombiner.spec
```

To bundle a custom icon, place an `app.ico` next to the spec and uncomment the
`icon=` line in `PDFCombiner.spec`.

## Logging

Errors and activity are written to `pdf_combiner.log` next to the executable
(or in the working directory when run from source). The log rotates at ~1 MB
with three backups.
```
