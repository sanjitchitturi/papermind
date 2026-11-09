"""Overlapping word windows with exact character offsets for page provenance."""

import re
from dataclasses import dataclass

from app.core.config import get_settings
from app.ingestion.pdf_parser import ParsedDocument, page_for_offset


@dataclass
class TextChunk:
    text: str
    section: str
    order: int
    page_start: int
    page_end: int
    token_count: int


def chunk_document(doc: ParsedDocument) -> list[TextChunk]:
    settings = get_settings()
    window = max(1, int(settings.chunk_target_tokens / 1.3))
    overlap = min(window - 1, int(settings.chunk_overlap_tokens / 1.3))
    chunks = []
    for i, (section, start) in enumerate(doc.section_offsets):
        end = doc.section_offsets[i + 1][1] if i + 1 < len(doc.section_offsets) else len(doc.full_text)
        words = list(re.finditer(r"\S+", doc.full_text[start:end]))
        for j in range(0, len(words), window - overlap):
            chosen = words[j : j + window]
            lo, hi = start + chosen[0].start(), start + chosen[-1].end()
            chunks.append(
                TextChunk(
                    text=doc.full_text[lo:hi],
                    section=section,
                    order=len(chunks),
                    page_start=page_for_offset(doc.page_offsets, lo),
                    page_end=page_for_offset(doc.page_offsets, hi - 1),
                    token_count=max(1, round(len(chosen) * 1.3)),
                )
            )
            if j + window >= len(words):
                break
    return chunks
