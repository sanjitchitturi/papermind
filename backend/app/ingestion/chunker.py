"""
Section-aware chunking with sentence-boundary cuts.

Plain fixed-size windows happily split a sentence (or a section heading)
across two chunks, which hurts both retrieval and citation. We chunk
inside each detected section, walk by sentences, and only fall back to
a word window if a single sentence is itself longer than the budget.
"""

from dataclasses import dataclass

from app.core.config import get_settings
from app.ingestion.pdf_parser import ParsedDocument, page_for_offset, section_for_offset

_SENTENCE_SPLIT = r"(?<=[.!?])\s+(?=[A-Z0-9\"])"


@dataclass
class TextChunk:
    text: str
    section: str
    order: int
    page_start: int
    page_end: int
    token_count: int


def _approx_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


def _sentences(text: str) -> list[str]:
    import re

    parts = re.split(_SENTENCE_SPLIT, text.strip())
    return [p.strip() for p in parts if p.strip()]


def _split_into_sections(doc: ParsedDocument) -> list[tuple[str, str, int]]:
    offsets = doc.section_offsets
    sections = []
    for i, (name, start) in enumerate(offsets):
        end = offsets[i + 1][1] if i + 1 < len(offsets) else len(doc.full_text)
        text = doc.full_text[start:end]
        if text.strip():
            sections.append((name, text, start))
    return sections


def chunk_document(doc: ParsedDocument) -> list[TextChunk]:
    settings = get_settings()
    target = settings.chunk_target_tokens
    overlap = settings.chunk_overlap_tokens
    chunks: list[TextChunk] = []
    order = 0

    for section_name, section_text, section_start in _split_into_sections(doc):
        name = section_name
        sentences = _sentences(section_text)
        if not sentences:
            continue

        current: list[str] = []
        current_tokens = 0
        cursor = section_start

        def emit(parts: list[str], start_offset: int, section: str = name) -> None:
            nonlocal order
            text = " ".join(parts).strip()
            if not text:
                return
            end_offset = start_offset + len(text)
            chunks.append(
                TextChunk(
                    text=text,
                    section=section or section_for_offset(doc.section_offsets, start_offset),
                    order=order,
                    page_start=page_for_offset(doc.page_offsets, start_offset),
                    page_end=page_for_offset(doc.page_offsets, end_offset),
                    token_count=_approx_tokens(text),
                )
            )
            order += 1

        for sentence in sentences:
            sent_tokens = _approx_tokens(sentence)
            if current and current_tokens + sent_tokens > target:
                emit(current, cursor)
                # Keep a trailing overlap so consecutive chunks share context.
                keep: list[str] = []
                keep_tokens = 0
                for s in reversed(current):
                    t = _approx_tokens(s)
                    if keep_tokens + t > overlap:
                        break
                    keep.append(s)
                    keep_tokens += t
                current = list(reversed(keep))
                current_tokens = keep_tokens
                cursor = section_start  # approximate; exact char offsets aren't needed downstream
            if sent_tokens > target and not current:
                # A single sentence longer than the budget, split on words.
                words = sentence.split()
                window = max(int(target / 1.3), 40)
                for i in range(0, len(words), window):
                    emit(words[i : i + window], cursor)
                continue
            current.append(sentence)
            current_tokens += sent_tokens

        if current:
            emit(current, cursor)

    return chunks
