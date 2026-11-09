from pathlib import Path

import pymupdf

from app.ingestion.bib_parser import _expand_marker_group
from app.ingestion.chunker import chunk_document
from app.ingestion.pdf_parser import parse_pdf


def test_chunk_pages_follow_actual_pdf_pages(tmp_path: Path):
    doc = pymupdf.open()
    for marker in ("firstpagemarker", "secondpagemarker"):
        page = doc.new_page()
        page.insert_textbox(
            pymupdf.Rect(40, 40, 550, 750), (marker + " evidence sentence with attention and research. ") * 40
        )
    path = tmp_path / "pages.pdf"
    doc.save(path)
    doc.close()
    parsed = parse_pdf(str(path))
    chunks = chunk_document(parsed)
    assert any(chunk.page_start == 2 for chunk in chunks)
    for chunk in chunks:
        if "firstpagemarker" in chunk.text:
            assert chunk.page_start == 1
        if "secondpagemarker" in chunk.text:
            assert chunk.page_end == 2


def test_bibliography_ranges_are_bounded():
    assert _expand_marker_group("1-999999999") == []
    assert _expand_marker_group("2-4") == ["2", "3", "4"]
