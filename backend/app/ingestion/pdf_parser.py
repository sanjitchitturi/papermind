import re
from dataclasses import dataclass, field

import pymupdf as fitz

from app.ingestion.text_cleanup import clean_page_text, drop_repeating_headers, finalize_document

SECTION_HEADING_PATTERN = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?("
    r"abstract|introduction|related work|background|preliminaries|"
    r"method(?:ology|s)?|approach|model(?:\s*architecture)?|"
    r"experiments?|evaluation|results?|"
    r"discussion|limitations|conclusion[s]?|future work|"
    r"acknowledg(?:e)?ments?|references|bibliography|appendix"
    r")\b.*$",
    re.IGNORECASE,
)

SECTION_ALIASES = {
    "bibliography": "references",
    "methods": "method",
    "methodology": "method",
    "experiment": "experiments",
    "result": "results",
    "conclusions": "conclusion",
    "acknowledgement": "acknowledgments",
    "acknowledgements": "acknowledgments",
}


@dataclass
class ParsedPage:
    page_number: int
    text: str


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    full_text: str
    # (section_name, start_char_offset) in full_text, in order
    section_offsets: list[tuple[str, int]]
    # start_char_offset of each page in full_text
    page_offsets: list[int] = field(default_factory=list)


def parse_pdf(path: str, max_pages: int | None = None) -> ParsedDocument:
    doc = fitz.open(path)
    try:
        page_count = doc.page_count
        if max_pages is not None:
            page_count = min(page_count, max_pages)
        raw_pages = [clean_page_text(doc[i].get_text("text")) for i in range(page_count)]
    finally:
        doc.close()

    cleaned_pages = drop_repeating_headers(raw_pages)
    pages = [ParsedPage(page_number=i + 1, text=text) for i, text in enumerate(cleaned_pages)]

    full_text_parts: list[str] = []
    page_offsets: list[int] = []
    section_offsets: list[tuple[str, int]] = [("preamble", 0)]
    offset = 0
    seen_sections: set[str] = set()

    for page in pages:
        page_offsets.append(offset)
        for line in page.text.splitlines():
            stripped = line.strip()
            match = SECTION_HEADING_PATTERN.match(stripped)
            if match and len(stripped) < 80:
                raw_name = match.group(1).lower()
                name = SECTION_ALIASES.get(raw_name, raw_name)
                if name not in seen_sections:
                    section_offsets.append((name, offset))
                    seen_sections.add(name)
            offset += len(line) + 1
        full_text_parts.append(page.text)
        offset += 1  # the "\n" joining pages

    full_text = finalize_document("\n".join(full_text_parts))
    return ParsedDocument(pages=pages, full_text=full_text, section_offsets=section_offsets, page_offsets=page_offsets)


def section_for_offset(section_offsets: list[tuple[str, int]], char_offset: int) -> str:
    current = section_offsets[0][0]
    for name, start in section_offsets:
        if start <= char_offset:
            current = name
        else:
            break
    return current


def page_for_offset(page_offsets: list[int], char_offset: int) -> int:
    page = 1
    for i, start in enumerate(page_offsets):
        if start <= char_offset:
            page = i + 1
        else:
            break
    return page
