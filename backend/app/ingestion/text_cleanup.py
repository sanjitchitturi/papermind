import re
import unicodedata

# Hyphen at the end of a line joining a word split by the page width.
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_MULTI_BLANK = re.compile(r"\n{3,}")
_SPACES = re.compile(r"[ \t]{2,}")
_PAGE_NUMBER_LINE = re.compile(r"^\s*\d+\s*$")
_FORM_FEED = "\x0c"

# Headers/footers that show up as a short line on at least this many pages.
_HEADER_REPEAT_RATIO = 0.4


def clean_page_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace(_FORM_FEED, "\n")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _SPACES.sub(" ", text)
    return text


def drop_repeating_headers(pages: list[str]) -> list[str]:
    if len(pages) < 3:
        return pages
    counts: dict[str, int] = {}
    for page in pages:
        for line in _edge_lines(page):
            counts[line] = counts.get(line, 0) + 1
    threshold = max(3, int(len(pages) * _HEADER_REPEAT_RATIO))
    drop = {line for line, n in counts.items() if n >= threshold and _looks_like_header(line)}
    if not drop:
        return pages
    cleaned = []
    for page in pages:
        kept = [ln for ln in page.splitlines() if ln.strip() not in drop and not _PAGE_NUMBER_LINE.match(ln)]
        cleaned.append("\n".join(kept))
    return cleaned


def finalize_document(text: str) -> str:
    text = _MULTI_BLANK.sub("\n\n", text)
    return text.strip()


def first_author_surname(authors: str) -> str:
    if not authors:
        return ""
    first = authors.split(",")[0].strip()
    if not first:
        return ""
    parts = first.split()
    return re.sub(r"[^A-Za-z\-]", "", parts[-1]).lower()


def year_from_arxiv_id(arxiv_id: str | None) -> int | None:
    if not arxiv_id:
        return None
    # New-style ids: YYMM.NNNNN  (1706.03762 -> 2017)
    match = re.match(r"^(\d{2})(\d{2})\.", arxiv_id)
    if match:
        yy = int(match.group(1))
        return 1900 + yy if yy >= 90 else 2000 + yy
    return None


def _edge_lines(page: str) -> list[str]:
    lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
    if not lines:
        return []
    take = min(3, len(lines))
    return lines[:take] + lines[-take:]


def _looks_like_header(line: str) -> bool:
    if len(line) > 90:
        return False
    if _PAGE_NUMBER_LINE.match(line):
        return True
    # A header is usually title-case or all-caps, not a full sentence.
    return not line.endswith((".", "?", "!"))
