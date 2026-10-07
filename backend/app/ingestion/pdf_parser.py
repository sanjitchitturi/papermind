"""
Turns a PDF on disk into plain text split by page, plus a best-effort
section map. Papers are not formatted consistently enough to parse
perfectly, so this leans on common heading patterns rather than trying to
be a full document-structure parser.
"""

import re
from dataclasses import dataclass

import pymupdf as fitz

# Covers the vast majority of paper section headings we see on arXiv.
# Order matters a little: longer/more specific patterns are listed first
# so "related work" doesn't get swallowed by a generic "work" match.
SECTION_HEADING_PATTERN = re.compile(
    r"^\s*(?:\d+\.?\s*)?("
    r"abstract|introduction|related work|background|"
    r"method(?:ology)?|approach|model(?:\s*architecture)?|"
    r"experiments?|evaluation|results?|"
    r"discussion|limitations|conclusion[s]?|"
    r"acknowledg(?:e)?ments?|references|appendix"
    r")\s*$",
    re.IGNORECASE,
)


@dataclass
class ParsedPage:
    page_number: int
    text: str


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    full_text: str
    # list of (section_name, start_char_offset) in full_text, in order
    section_offsets: list[tuple[str, int]]


def parse_pdf(path: str) -> ParsedDocument:
    doc = fitz.open(path)
    pages: list[ParsedPage] = []
    full_text_parts: list[str] = []
    offset = 0
    section_offsets: list[tuple[str, int]] = [("preamble", 0)]

    for page_index in range(doc.page_count):
        page_text = doc[page_index].get_text("text")
        pages.append(ParsedPage(page_number=page_index + 1, text=page_text))

        for line in page_text.splitlines():
            match = SECTION_HEADING_PATTERN.match(line.strip())
            if match:
                section_name = match.group(1).lower()
                section_offsets.append((section_name, offset))
            offset += len(line) + 1

        full_text_parts.append(page_text)

    doc.close()
    full_text = "\n".join(full_text_parts)
    return ParsedDocument(pages=pages, full_text=full_text, section_offsets=section_offsets)


def section_for_offset(section_offsets: list[tuple[str, int]], char_offset: int) -> str:
    """Finds which section a given character offset in full_text falls into."""
    current = section_offsets[0][0]
    for name, start in section_offsets:
        if start <= char_offset:
            current = name
        else:
            break
    return current
