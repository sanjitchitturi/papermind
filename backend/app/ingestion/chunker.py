"""
Section-aware chunking.

Plain fixed-size chunking will happily cut a chunk in half across an
Abstract/Introduction boundary, which hurts retrieval precision because
the chunk ends up being "about" two different things. Instead we chunk
within each detected section and only fall back to a sliding window once
we are inside a single section's text.

Token counts here are approximated as word counts (words * 1.3 is a
reasonable rule of thumb vs. a real tokenizer). That is good enough for
sizing chunks consistently and avoids pulling in tiktoken as a dependency
just for this.
"""

from dataclasses import dataclass

from app.core.config import get_settings
from app.ingestion.pdf_parser import ParsedDocument

settings = get_settings()


@dataclass
class Chunk:
    text: str
    section: str
    order: int
    char_start: int
    char_end: int


def _approx_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def _split_into_sections(doc: ParsedDocument) -> list[tuple[str, str, int]]:
    """Returns (section_name, section_text, start_offset) for each contiguous section."""
    offsets = doc.section_offsets
    sections = []
    for i, (name, start) in enumerate(offsets):
        end = offsets[i + 1][1] if i + 1 < len(offsets) else len(doc.full_text)
        text = doc.full_text[start:end]
        if text.strip():
            sections.append((name, text, start))
    return sections


def chunk_document(doc: ParsedDocument) -> list[Chunk]:
    target = settings.chunk_target_tokens
    overlap = settings.chunk_overlap_tokens
    chunks: list[Chunk] = []
    order = 0

    for section_name, section_text, section_start in _split_into_sections(doc):
        words = section_text.split()
        if not words:
            continue

        # Walk the section in a sliding window measured in words, which
        # keeps the implementation simple while still respecting the
        # token budget closely enough for chunk sizing purposes.
        window_words = int(target / 1.3)
        overlap_words = int(overlap / 1.3)
        step = max(window_words - overlap_words, 1)

        start_word = 0
        while start_word < len(words):
            end_word = min(start_word + window_words, len(words))
            chunk_words = words[start_word:end_word]
            chunk_text = " ".join(chunk_words)

            chunks.append(
                Chunk(
                    text=chunk_text,
                    section=section_name,
                    order=order,
                    char_start=section_start,  # approximate, exact char offsets aren't needed downstream
                    char_end=section_start + len(chunk_text),
                )
            )
            order += 1

            if end_word == len(words):
                break
            start_word += step

    return chunks
