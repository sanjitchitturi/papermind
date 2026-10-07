"""
Wraps the arxiv.org API for search and for fetching a specific paper by
id, then downloads the PDF so the rest of ingestion can treat it the same
way as an uploaded file.
"""

import os
import re
from dataclasses import dataclass

import arxiv

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
    filename = f"{short_id.replace('/', '_')}.pdf"
    pdf_path = os.path.join(storage, filename)
    if not os.path.exists(pdf_path):
        result.download_pdf(dirpath=storage, filename=filename)

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
