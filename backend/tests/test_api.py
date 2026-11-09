from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import get_settings
from app.db.models import AnswerRecord, Chunk, Claim, Contradiction, Paper
from app.db.session import engine
from app.main import app


@pytest.fixture
def client():
    SQLModel.metadata.drop_all(engine)
    with TestClient(app) as client:
        yield client


def pdf_bytes():
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(
        pymupdf.Rect(40, 40, 550, 750),
        "Introduction\n"
        + "Retrieval combines evidence from research documents. BM25 ranks relevant passages using document frequency. "
        * 10,
    )
    data = doc.tobytes()
    doc.close()
    return data


def test_offline_demo_chat_research_graph_and_feedback(client):
    assert client.get("/api/health").json()["database"] is True
    assert client.get("/api/capabilities").json()["search_mode"] == "bm25"
    assert client.post("/api/demo/seed").json() == {"papers": 3, "created": 3}
    assert client.post("/api/demo/seed").json()["created"] == 0
    papers = client.get("/api/papers").json()
    assert len(papers) == 3
    assert all(p["source"] == "sample" for p in papers)
    answer = client.post("/api/chat", json={"question": "How does BM25 rank passages?"}).json()
    assert answer["mode"] == "extractive"
    assert answer["sources"]
    assert "not a probability" in answer["trust_explanation"]
    feedback = client.post("/api/feedback", json={"answer_id": answer["answer_id"], "rating": 1})
    assert feedback.status_code == 200
    assert client.post("/api/research", json={"question": "How does retrieval use evidence?"}).json()["matrix"]
    assert client.get("/api/graph").json()["nodes"]
    assert client.post(f"/api/graph/papers/{papers[0]['id']}/build").status_code == 200
    assert client.get(f"/api/graph/papers/{papers[0]['id']}/related").status_code == 200
    assert client.get("/api/eval/history").json() == []
    assert client.post("/api/integrity/contradictions/scan").status_code == 503
    assert client.get("/api/integrity/contradictions").json() == []
    assert client.post(f"/api/integrity/papers/{papers[0]['id']}/check").status_code == 503
    assert client.get(f"/api/integrity/papers/{papers[0]['id']}/report").status_code == 200


def test_unverified_generated_answer_falls_back_to_quotes(client, monkeypatch):
    from app.api import routes_chat
    from app.generation.answer_generator import GeneratedAnswer, Source

    client.post("/api/demo/seed")
    source = Source(1, "chunk", "paper", "Paper", "intro", 1, "Verified source passage.")
    monkeypatch.setattr(
        routes_chat, "generate_answer",
        lambda *_: GeneratedAnswer("Unsupported claim [1].", [source], "generative"),
    )
    monkeypatch.setattr(routes_chat, "verify_citations", lambda *_: [])
    answer = client.post("/api/chat", json={"question": "What does the paper say?"}).json()
    assert answer["mode"] == "extractive"
    assert "Verified source passage." in answer["answer"]
    assert "Unsupported claim" not in answer["answer"]


def test_upload_search_restart_and_delete_cleans_dependencies(client):
    response = client.post(
        "/api/ingest/upload", files={"file": ("../../paper.pdf", BytesIO(pdf_bytes()), "application/pdf")}
    )
    assert response.status_code == 200, response.text
    job = client.get(f"/api/ingest/jobs/{response.json()['job_id']}").json()
    assert job["status"] == "done", job
    paper_id = job["result"]["paper_id"]
    assert not list((Path(get_settings().storage_dir) / "uploads").iterdir())
    paper = client.get(f"/api/papers/{paper_id}").json()
    assert paper["title"] == "paper"
    answer = client.post("/api/chat", json={"question": "What does BM25 rank?", "paper_id": paper_id})
    assert answer.status_code == 200, answer.text
    assert answer.json()["sources"]
    assert client.post("/api/feedback", json={"answer_id": answer.json()["answer_id"], "rating": 1}).status_code == 200
    # A separate engine/process can read the same persisted library.
    restarted = create_engine(get_settings().database_url)
    with Session(restarted) as session:
        assert len(session.exec(select(Chunk)).all()) > 0
    restarted.dispose()
    with Session(engine) as session:
        paper = session.exec(select(Paper)).first()
        a = Claim(paper_id=paper.id, kind="atomic", claim_text="Evidence matters")
        b = Claim(paper_id=paper.id, kind="atomic", claim_text="More evidence matters")
        session.add(a)
        session.add(b)
        session.flush()
        session.add(Contradiction(claim_a_id=a.id, claim_b_id=b.id, explanation="test"))
        session.commit()
    assert client.delete(f"/api/papers/{paper_id}").status_code == 200
    assert client.get("/api/papers").json() == []
    with Session(engine) as session:
        assert session.exec(select(Chunk)).all() == []
        assert session.exec(select(Contradiction)).all() == []
        assert session.exec(select(AnswerRecord)).first().paper_id is None


def test_invalid_pdf_fails_without_partial_paper(client):
    response = client.post("/api/ingest/upload", files={"file": ("bad.pdf", b"not a pdf", "application/pdf")})
    job = client.get(f"/api/ingest/jobs/{response.json()['job_id']}").json()
    assert job["status"] == "failed"
    assert client.get("/api/papers").json() == []
    assert client.post("/api/ingest/upload", files={"file": ("bad.txt", b"text")}).status_code == 400
    assert client.post("/api/ingest/upload", files={"file": ("empty.pdf", b"")}).status_code == 400


def test_ids_input_errors_and_empty_retrieval(client):
    assert client.post("/api/chat", json={"question": "hello", "paper_id": "invalid"}).status_code == 400
    assert client.post("/api/chat", json={"question": "hello", "paper_id": str(uuid4())}).status_code == 404
    answer = client.post("/api/chat", json={"question": "missing evidence"}).json()
    assert answer["sources"] == [] and answer["trust_score"] == 0
    assert client.post("/api/feedback", json={"answer_id": str(uuid4()), "rating": 1}).status_code == 404
    assert client.get("/api/ingest/jobs/invalid").status_code == 400
    assert client.post("/api/eval/run?suite=invalid").status_code == 422
    assert client.post("/api/ingest/arxiv", json={"arxiv_id": "nonsense"}).status_code == 400
    assert client.get("/api/no-such-route").status_code == 404


def test_untrusted_cross_origin_write_is_rejected(client):
    response = client.post("/api/demo/seed", headers={"origin": "https://untrusted.example"})
    assert response.status_code == 403


def test_retrieval_eval_runs_offline_and_reports_only_bm25(client):
    response = client.post("/api/eval/run")
    job = client.get(f"/api/ingest/jobs/{response.json()['job_id']}").json()
    assert job["status"] == "done", job
    metrics = job["result"]["metrics"]
    assert "bm25_mrr" in metrics
    assert not any("hybrid" in key or "dense" in key for key in metrics)
    assert len(client.get("/api/eval/history").json()) == 1
