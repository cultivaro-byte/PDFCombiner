"""Tests for the Qt-independent core: ordering, ZIP handling and merging.

Run with::

    pip install pypdf pytest
    pytest
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from pdf_combiner import config
from pdf_combiner.pdf_locator import find_pdfs
from pdf_combiner.pdf_merger import PdfMergeError, merge_pdfs, order_pdfs
from pdf_combiner.processor import process_archive
from pdf_combiner.zip_handler import ZipExtractionError, extract_zip


def _make_pdf(path: Path, pages: int = 1) -> None:
    """Write a minimal valid PDF with *pages* blank pages."""

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        writer.write(handle)


# --------------------------------------------------------------- ordering --
def test_order_pdfs_alphabetical(tmp_path: Path) -> None:
    files = [tmp_path / n for n in ("c.pdf", "a.pdf", "B.pdf")]
    ordered = order_pdfs(files)
    assert [p.name for p in ordered] == ["a.pdf", "B.pdf", "c.pdf"]


def test_order_pdfs_specials_appended_last(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        config, "SPECIAL_PDF_ORDER", ("zzz_last.pdf", "appendix.pdf")
    )
    files = [
        tmp_path / "appendix.pdf",
        tmp_path / "b.pdf",
        tmp_path / "zzz_last.pdf",
        tmp_path / "a.pdf",
    ]
    ordered = [p.name for p in order_pdfs(files)]
    # Regular sorted first, then specials in configured order.
    assert ordered == ["a.pdf", "b.pdf", "zzz_last.pdf", "appendix.pdf"]


def test_order_pdfs_missing_special_skipped(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        config, "SPECIAL_PDF_ORDER", ("present.pdf", "missing.pdf")
    )
    files = [tmp_path / "a.pdf", tmp_path / "present.pdf"]
    ordered = [p.name for p in order_pdfs(files)]
    assert ordered == ["a.pdf", "present.pdf"]  # 'missing.pdf' simply skipped


# ----------------------------------------------------------- zip handling --
def test_extract_valid_zip(tmp_path: Path) -> None:
    zip_path = tmp_path / "good.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("a.txt", "hello")
        zf.writestr("sub/b.txt", "world")

    dest = tmp_path / "out"
    extract_zip(zip_path, dest)
    assert (dest / "a.txt").exists()
    assert (dest / "sub" / "b.txt").exists()


def test_extract_invalid_zip_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"this is not a zip file")
    with pytest.raises(ZipExtractionError):
        extract_zip(bad, tmp_path / "out")


def test_extract_missing_zip_raises(tmp_path: Path) -> None:
    with pytest.raises(ZipExtractionError):
        extract_zip(tmp_path / "nope.zip", tmp_path / "out")


# ------------------------------------------------------------- discovery ---
def test_find_pdfs_recursive(tmp_path: Path) -> None:
    _make_pdf(tmp_path / "top.pdf")
    _make_pdf(tmp_path / "nested" / "deep" / "inner.pdf")
    (tmp_path / "note.txt").write_text("ignore me")
    found = {p.name for p in find_pdfs(tmp_path)}
    assert found == {"top.pdf", "inner.pdf"}


# --------------------------------------------------------------- merging ---
def test_merge_pdfs(tmp_path: Path) -> None:
    _make_pdf(tmp_path / "a.pdf", pages=2)
    _make_pdf(tmp_path / "b.pdf", pages=3)
    out = tmp_path / "merged.pdf"
    count = merge_pdfs([tmp_path / "a.pdf", tmp_path / "b.pdf"], out)
    assert count == 2
    assert len(PdfReader(out).pages) == 5


def test_merge_skips_corrupt_but_succeeds(tmp_path: Path) -> None:
    _make_pdf(tmp_path / "good.pdf", pages=1)
    (tmp_path / "broken.pdf").write_bytes(b"%PDF-1.4 broken")
    out = tmp_path / "merged.pdf"
    count = merge_pdfs([tmp_path / "broken.pdf", tmp_path / "good.pdf"], out)
    assert count == 1  # only the good one


def test_merge_all_corrupt_raises(tmp_path: Path) -> None:
    (tmp_path / "broken.pdf").write_bytes(b"not a pdf")
    with pytest.raises(PdfMergeError):
        merge_pdfs([tmp_path / "broken.pdf"], tmp_path / "out.pdf")


# ------------------------------------------------- end-to-end per archive --
def test_process_archive_end_to_end(tmp_path: Path) -> None:
    # Build a source tree, zip it, then process it.
    src = tmp_path / "src"
    _make_pdf(src / "a.pdf")
    _make_pdf(src / "folder" / "b.pdf")
    zip_path = tmp_path / "Application_123.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for pdf in src.rglob("*.pdf"):
            zf.write(pdf, pdf.relative_to(src))

    out_dir = tmp_path / "output"
    result = process_archive(zip_path, out_dir)

    assert result.success
    assert result.output_path == out_dir / "Application_123.pdf"
    assert result.output_path.exists()
    assert result.merged_count == 2


def test_process_archive_no_pdfs(tmp_path: Path) -> None:
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("readme.txt", "no pdfs here")
    result = process_archive(zip_path, tmp_path / "out")
    assert not result.success
    assert "No PDF" in result.message
