from app.ingestion.bib_parser import extract_bibliography, find_in_text_citations


def test_find_in_text_citations_single_marker():
    text = "Prior work has shown this approach works well [12]. We build on it."
    citations = find_in_text_citations(text)
    assert len(citations) == 1
    assert citations[0].marker == "12"


def test_find_in_text_citations_expands_ranges_and_lists():
    text = "Several studies [1, 2] and others [5-7] support this claim."
    citations = find_in_text_citations(text)
    markers = sorted(int(c.marker) for c in citations)
    assert markers == [1, 2, 5, 6, 7]


def test_extract_bibliography_parses_numbered_entries():
    references_text = (
        "[1] Vaswani et al. Attention Is All You Need. arXiv:1706.03762, 2017.\n"
        "[2] Devlin et al. BERT: Pre-training of Deep Bidirectional Transformers. 2018.\n"
    )
    entries = extract_bibliography(references_text)
    assert len(entries) == 2
    assert entries[0].marker == "1"
    assert entries[0].resolved_arxiv_id == "1706.03762"
    assert entries[1].resolved_arxiv_id is None
