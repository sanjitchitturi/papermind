from app.ingestion.chunker import chunk_document
from app.ingestion.pdf_parser import ParsedDocument


def _make_doc(section_texts: dict[str, str]) -> ParsedDocument:
    full_text = ""
    section_offsets = []
    for name, text in section_texts.items():
        section_offsets.append((name, len(full_text)))
        full_text += text
    return ParsedDocument(pages=[], full_text=full_text, section_offsets=section_offsets)


def test_chunks_stay_within_their_section():
    doc = _make_doc(
        {
            "abstract": "word " * 50,
            "introduction": "intro " * 600,  # long enough to need multiple chunks
        }
    )
    chunks = chunk_document(doc)
    sections_seen = {c.section for c in chunks}
    assert "abstract" in sections_seen
    assert "introduction" in sections_seen
    # no chunk should mix words from both sections
    for c in chunks:
        if c.section == "abstract":
            assert "intro" not in c.text
        if c.section == "introduction":
            assert "word" not in c.text


def test_long_section_produces_overlapping_chunks():
    doc = _make_doc({"method": "token " * 2000})
    chunks = chunk_document(doc)
    assert len(chunks) > 1
    # consecutive chunks should share some overlapping words given the configured overlap
    first_words = set(chunks[0].text.split())
    second_words = set(chunks[1].text.split())
    assert first_words & second_words
