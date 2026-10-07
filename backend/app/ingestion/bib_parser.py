"""
Parses a paper's reference list and finds where each reference is cited
in the body text.

This is intentionally regex-based rather than using a heavyweight citation
parser. arXiv papers are messy and inconsistent enough that a "good
enough, handles the common cases" parser is more maintainable than trying
to perfectly handle every formatting style. The Citation Integrity Engine
only needs to find *most* citations to be useful, it doesn't need all of
them.
"""

import re
from dataclasses import dataclass

# Numeric style: [12], [12, 13], [12-14]
NUMERIC_MARKER_PATTERN = re.compile(r"\[(\d+(?:\s*[,-]\s*\d+)*)\]")

# Author-year style: (Vaswani et al., 2017) or (Smith and Jones, 2019)
AUTHOR_YEAR_PATTERN = re.compile(r"\(([A-Z][\w\-]+(?:\s+(?:et al\.|and\s+[A-Z][\w\-]+))?,?\s*(\d{4}))\)")

# A reference list entry starting with "[12]" or "12."
NUMERIC_ENTRY_PATTERN = re.compile(r"^\s*\[(\d+)\]\s*(.+)", re.MULTILINE)

ARXIV_ID_PATTERN = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})", re.IGNORECASE)


@dataclass
class BibEntry:
    marker: str
    raw_text: str
    resolved_arxiv_id: str | None


@dataclass
class InTextCitation:
    marker: str
    char_offset: int
    context: str  # the sentence or nearby text the citation appears in


def extract_bibliography(references_text: str) -> list[BibEntry]:
    """Parses the References section into individual entries, numeric style only for now."""
    matches = list(NUMERIC_ENTRY_PATTERN.finditer(references_text))
    entries: list[BibEntry] = []
    for i, match in enumerate(matches):
        marker, body_start = match.group(1), match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(references_text)
        raw_text = references_text[body_start:end].strip()
        arxiv_match = ARXIV_ID_PATTERN.search(raw_text)
        entries.append(
            BibEntry(
                marker=marker,
                raw_text=raw_text,
                resolved_arxiv_id=arxiv_match.group(1) if arxiv_match else None,
            )
        )
    return entries


def find_in_text_citations(body_text: str) -> list[InTextCitation]:
    """
    Finds numeric citation markers in the body text and grabs the
    surrounding sentence as context, since that is what the claim
    extractor needs to figure out what claim is being attributed to the
    citation.
    """
    citations: list[InTextCitation] = []
    for match in NUMERIC_MARKER_PATTERN.finditer(body_text):
        marker_group = match.group(1)
        # "[12, 13]" or "[12-14]" can reference multiple works, split them out
        for marker in _expand_marker_group(marker_group):
            context = _sentence_around(body_text, match.start(), match.end())
            citations.append(InTextCitation(marker=marker, char_offset=match.start(), context=context))
    return citations


def _expand_marker_group(group: str) -> list[str]:
    markers: list[str] = []
    for part in group.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-")
            markers.extend(str(n) for n in range(int(lo), int(hi) + 1))
        elif part:
            markers.append(part)
    return markers


def _sentence_around(text: str, start: int, end: int, window: int = 300) -> str:
    lo = max(0, start - window)
    hi = min(len(text), end + window)
    snippet = text[lo:hi]
    # Trim to the nearest sentence boundaries so we don't hand the LLM a
    # half-sentence on either end.
    first_period = snippet.find(". ")
    if first_period != -1 and first_period < window:
        snippet = snippet[first_period + 2 :]
    return snippet.strip()
