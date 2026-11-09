import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session  # noqa: E402

from app.core.jobs import JobContext  # noqa: E402
from app.db.models import Job, JobKind, PaperSource  # noqa: E402
from app.db.session import engine, init_db  # noqa: E402
from app.ingestion.pipeline import ingest_paper  # noqa: E402

DATASET_PATH = Path(__file__).parent.parent / "app" / "eval" / "eval_dataset.json"


def main() -> None:
    init_db()

    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    with Session(engine) as session:
        for arxiv_id in dataset["seed_papers"]:
            print(f"Ingesting {arxiv_id}...")
            job = Job(
                kind=JobKind.ingest, input_json=json.dumps({"source": PaperSource.arxiv.value, "arxiv_id": arxiv_id})
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            result = ingest_paper(
                session,
                JobContext(job.id),
                {"source": PaperSource.arxiv.value, "arxiv_id": arxiv_id},
            )
            print(f"  -> {result}")


if __name__ == "__main__":
    main()
