import os
import re
import tempfile
from dataclasses import dataclass

import arxiv
import httpx

from app.core.config import get_settings

_ARXIV_ID = re.compile(r"^(?:\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})$")


@dataclass
class ArxivResult:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    pdf_path: str
    published: str | None


def search(query: str, max_results: int = 8) -> list[dict]:
    client = arxiv.Client()
    search_obj = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    results = []
    for result in client.results(search_obj):
        results.append(
            {
                "arxiv_id": _canonical_id(result.get_short_id()),
                "title": _one_line(result.title),
                "authors": [a.name for a in result.authors],
                "abstract": _one_line(result.summary),
                "published": result.published.date().isoformat() if result.published else None,
            }
        )
    return results


def fetch_and_download(arxiv_id: str) -> ArxivResult:
    canonical = _canonical_id(arxiv_id)
    if not _ARXIV_ID.match(canonical):
        raise ValueError(f"'{arxiv_id}' does not look like an arXiv id.")

    storage = os.path.join(get_settings().storage_dir, "papers")
    os.makedirs(storage, exist_ok=True)

    client = arxiv.Client()
    result = next(client.results(arxiv.Search(id_list=[canonical])), None)
    if result is None:
        raise ValueError(f"No arXiv paper found for id {canonical}")

    short_id = _canonical_id(result.get_short_id())
    if not _ARXIV_ID.fullmatch(short_id):
        raise ValueError("Invalid paper identifier returned by arXiv.")
    filename = f"{short_id.replace('/', '_')}.pdf"
    pdf_path = os.path.join(storage, filename)
    if not os.path.exists(pdf_path):
        # Derive the destination from a validated ID, never a metadata URL.
        limit = get_settings().max_upload_mb * 1024 * 1024
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=storage, suffix=".part", delete=False) as handle:
                temporary = handle.name
                with httpx.stream(
                    "GET", f"https://arxiv.org/pdf/{canonical}", timeout=30, follow_redirects=False
                ) as response:
                    response.raise_for_status()
                    size = 0
                    for chunk in response.iter_bytes(65536):
                        size += len(chunk)
                        if size > limit:
                            raise ValueError("PDF exceeds the upload limit.")
                        handle.write(chunk)
            with open(temporary, "rb") as handle:
                if not handle.read(5).startswith(b"%PDF-"):
                    raise ValueError("The downloaded document is not a PDF.")
            os.replace(temporary, pdf_path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    return ArxivResult(
        arxiv_id=short_id,
        title=_one_line(result.title),
        authors=[a.name for a in result.authors],
        abstract=_one_line(result.summary),
        pdf_path=pdf_path,
        published=result.published.date().isoformat() if result.published else None,
    )


def _canonical_id(arxiv_id: str) -> str:
    return arxiv_id.strip().replace("arxiv:", "").replace("arXiv:", "").split("v")[0]


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
