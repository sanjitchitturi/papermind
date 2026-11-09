from app.ingestion.text_cleanup import clean_page_text, drop_repeating_headers, first_author_surname, year_from_arxiv_id


def test_hyphenated_line_breaks_are_joined():
    text = clean_page_text("transfor-\nmation of the input")
    assert "transformation" in text
    assert "transfor-\n" not in text


def test_repeating_headers_are_dropped():
    pages = [
        "Attention Is All You Need\nThe Transformer architecture\n1",
        "Attention Is All You Need\nUses self-attention instead of recurrence\n2",
        "Attention Is All You Need\nMulti-head attention is used\n3",
    ]
    cleaned = drop_repeating_headers(pages)
    assert all("Attention Is All You Need" not in p for p in cleaned)
    assert "self-attention" in cleaned[1]


def test_author_surname_and_year():
    assert first_author_surname("Ashish Vaswani, Noam Shazeer") == "vaswani"
    assert year_from_arxiv_id("1706.03762") == 2017
    assert year_from_arxiv_id("1810.04805") == 2018
