"""
Ingests the seed papers listed in eval_dataset.json synchronously, so CI
(and local dev, if you want a quick starting corpus) has something real
to retrieve against before the eval suite runs. The normal ingestion path
runs as a background task behind a job id, this script just calls the
same pipeline function directly and waits for it to finish.
"""

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session  # noqa: E402

from app.db.models import IngestionJob, JobStatus, PaperSource  # noqa: E402
from app.db.session import engine, init_db  # noqa: E402
from app.ingestion import arxiv_fetcher  # noqa: E402
from app.ingestion.pipeline import ingest_paper  # noqa: E402

DATASET_PATH = Path(__file__).parent.parent / "app" / "eval" / "eval_dataset.json"


def main() -> None:
    init_db()
    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    with Session(engine) as session:
        for arxiv_id in dataset["seed_papers"]:
            print(f"Fetching {arxiv_id}...")
            result = arxiv_fetcher.fetch_and_download(arxiv_id)

            job = IngestionJob(id=uuid4(), status=JobStatus.queued, stage="seeding")
            session.add(job)
            session.commit()

            ingest_paper(
                session,
                job.id,
                pdf_path=result.pdf_path,
                title=result.title,
                authors=", ".join(result.authors),
                abstract=result.abstract,
                source=PaperSource.arxiv,
                arxiv_id=result.arxiv_id,
            )
            print(f"Ingested {arxiv_id}: {result.title}")


if __name__ == "__main__":
    main()
