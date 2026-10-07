"""
Wraps the arxiv.org API for both searching ("find me papers about X") and
fetching a specific paper by id, then downloads the PDF to local disk so
the rest of the ingestion pipeline can treat it the same way as an
uploaded file.
"""

import os
from dataclasses import dataclass

import arxiv

STORAGE_DIR = os.environ.get("PAPER_STORAGE_DIR", "./storage/papers")


@dataclass
class ArxivResult:
    arxiv_id: str
    version: str
    title: str
    authors: list[str]
    abstract: str
    pdf_path: str


def search(query: str, max_results: int = 10) -> list[dict]:
    client = arxiv.Client()
    search_obj = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    results = []
    for result in client.results(search_obj):
        results.append(
            {
                "arxiv_id": result.get_short_id(),
                "title": result.title,
                "authors": [a.name for a in result.authors],
                "abstract": result.summary,
                "published": result.published.isoformat() if result.published else None,
            }
        )
    return results


def fetch_and_download(arxiv_id: str) -> ArxivResult:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    client = arxiv.Client()
    search_obj = arxiv.Search(id_list=[arxiv_id])
    result = next(client.results(search_obj), None)
    if result is None:
        raise ValueError(f"No arXiv paper found for id {arxiv_id}")

    short_id = result.get_short_id()
    filename = f"{short_id.replace('/', '_')}.pdf"
    pdf_path = os.path.join(STORAGE_DIR, filename)
    result.download_pdf(dirpath=STORAGE_DIR, filename=filename)

    return ArxivResult(
        arxiv_id=short_id,
        version=short_id.split("v")[-1] if "v" in short_id else "1",
        title=result.title,
        authors=[a.name for a in result.authors],
        abstract=result.summary,
        pdf_path=pdf_path,
    )
