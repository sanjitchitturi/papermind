"""
Parses a paper's reference list and finds in-text citations.

This is regex-based on purpose. arXiv papers are inconsistent enough that
a "good enough, handles the common cases" parser is more maintainable than
trying to perfectly handle every formatting style. The integrity engine
only needs most citations to be useful, not all of them.
"""

import re
from dataclasses import dataclass

# Numeric: [12], [12, 13], [12-14]
NUMERIC_MARKER_PATTERN = re.compile(r"\[(\d+(?:\s*[,\-–]\s*\d+)*)\]")
NUMERIC_ENTRY_PATTERN = re.compile(r"^\s*\[(\d+)\]\s*(.+)", re.MULTILINE)

# Author-year in-text: (Vaswani et al., 2017)
AUTHOR_YEAR_INTEXT = re.compile(
    r"\(([A-Z][\w\-]+(?:\s+et\s+al\.|\s+and\s+[A-Z][\w\-]+)?),?\s*(\d{4})[a-z]?\)"
)

ARXIV_ID_PATTERN = re.compile(
    r"(?:arXiv:\s*)?((?:\d{4}\.\d{4,5})|(?:[a-z\-]+(?:\.[A-Z]{2})?/\d{7}))",
    re.IGNORECASE,
)
DOI_ARXIV = re.compile(r"10\.48550/arXiv\.(\d{4}\.\d{4,5})", re.IGNORECASE)
ABS_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", re.IGNORECASE)

# First author + year from a typical "Vaswani, A., ... (2017)" line.
AUTHOR_YEAR_ENTRY = re.compile(
    r"^[\s\[]*(?:\d+[\].]?\s*)?([A-Z][\w\-]+)[^,\n]{0,40}?.*?((?:19|20)\d{2})"
)


@dataclass
class BibEntry:
    marker: str
    raw_text: str
    resolved_arxiv_id: str | None
    first_author: str | None
    year: int | None


@dataclass
class InTextCitation:
    marker: str
    char_offset: int
    context: str


def extract_bibliography(references_text: str) -> list[BibEntry]:
    numeric = _numeric_entries(references_text)
    if numeric:
        return numeric
    return _split_paragraph_entries(references_text)


def find_in_text_citations(body_text: str) -> list[InTextCitation]:
    citations: list[InTextCitation] = []
    for match in NUMERIC_MARKER_PATTERN.finditer(body_text):
        for marker in _expand_marker_group(match.group(1)):
            citations.append(
                InTextCitation(marker=marker, char_offset=match.start(), context=_sentence_around(body_text, match.start(), match.end()))
            )
    if citations:
        return citations
    for match in AUTHOR_YEAR_INTEXT.finditer(body_text):
        marker = f"{match.group(1).split()[0]}{match.group(2)}"
        citations.append(
            InTextCitation(marker=marker, char_offset=match.start(), context=_sentence_around(body_text, match.start(), match.end()))
        )
    return citations


def extract_arxiv_id(text: str) -> str | None:
    for pattern in (DOI_ARXIV, ABS_URL):
        match = pattern.search(text)
        if match:
            return match.group(1)
    match = ARXIV_ID_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def _numeric_entries(text: str) -> list[BibEntry]:
    matches = list(NUMERIC_ENTRY_PATTERN.finditer(text))
    entries: list[BibEntry] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw = text[match.start() : end].strip()
        entries.append(_entry(match.group(1), raw))
    return entries


def _split_paragraph_entries(text: str) -> list[BibEntry]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if len(b.strip()) > 40]
    entries = []
    for i, block in enumerate(blocks, start=1):
        parsed_year = AUTHOR_YEAR_ENTRY.search(block)
        marker = f"{parsed_year.group(1)}{parsed_year.group(2)}" if parsed_year else str(i)
        entries.append(_entry(marker, block))
    return entries


def _entry(marker: str, raw: str) -> BibEntry:
    author_year = AUTHOR_YEAR_ENTRY.search(raw)
    year = int(author_year.group(2)) if author_year else None
    first_author = author_year.group(1).lower() if author_year else None
    return BibEntry(
        marker=marker,
        raw_text=raw,
        resolved_arxiv_id=extract_arxiv_id(raw),
        first_author=first_author,
        year=year,
    )


def _expand_marker_group(group: str) -> list[str]:
    markers: list[str] = []
    for part in re.split(r"[,]", group):
        part = part.strip().replace("–", "-")
        if "-" in part:
            lo, hi = part.split("-", 1)
            try:
                markers.extend(str(n) for n in range(int(lo), int(hi) + 1))
            except ValueError:
                if part:
                    markers.append(part)
        elif part:
            markers.append(part)
    return markers


def _sentence_around(text: str, start: int, end: int, window: int = 280) -> str:
    lo = max(0, start - window)
    hi = min(len(text), end + window)
    snippet = text[lo:hi]
    first_period = snippet.find(". ")
    if 0 < first_period < window // 2:
        snippet = snippet[first_period + 2 :]
    last_period = snippet.rfind(". ")
    if last_period > len(snippet) - window // 3 and last_period != -1:
        snippet = snippet[: last_period + 1]
    return snippet.strip()
