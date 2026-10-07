# PaperMind

A retrieval system for research papers that does more than chat with a PDF.

Live: [papermind-silk.vercel.app](https://papermind-silk.vercel.app)
API: [papermind-api-laof.onrender.com](https://papermind-api-laof.onrender.com/docs)
Source: this repository

Retrieval and reranking run on local int8 ONNX models. Generation, citation
integrity, and multi-paper research mode are optional and use any
OpenAI-compatible API when a key is present. Without a key the system still
searches, reranks, and returns extractive answers.

## Why this exists

Most RAG-for-papers projects stop at: chunk a PDF, embed it, answer with
citations. That is necessary, and it is also what ChatPDF, SciSpace, and a
dozen GitHub demos already do. PaperMind keeps that core and adds things
those tools typically skip:

1. **Hybrid retrieval with a measured reranker.** Dense + BM25 fused with
   reciprocal rank fusion, then a cross-encoder over the fused candidates.
   The eval dashboard reports dense, sparse, hybrid, and hybrid+rerank as
   separate ablations. If the reranker does not move MRR, that shows up.
2. **Citation integrity.** For each in-text citation, extract the claim
   attributed to the cited work, retrieve a passage from that work if it is
   in the library, and judge support. Unresolved citations stay unresolved.
3. **Trust scores that can abstain.** Retrieval margin, reranker
   confidence, citation pass rate, and self-consistency combine into a 0-100
   score. Below a threshold the system says it is not confident.

## Architecture

```
PDF / arXiv
    -> parse, clean, section-aware sentence chunks
    -> local dense encoder + BM25 sparse vectors
    -> Qdrant (RRF fusion)
    -> MiniLM cross-encoder rerank
    -> extractive quotes  or  LLM generation + citation verify + trust
Postgres holds papers, claims, citation checks, entities, jobs, eval runs.
```

Stack: FastAPI, SQLModel, Alembic, Postgres, Qdrant, fastembed/onnxruntime,
React, Vite, Tailwind.

## Models

Chosen so the whole API, including ONNX sessions, fits on Render's free plan
(512 MB). Weights are int8 quantized.

| Role | Model | Size | Notes |
| --- | --- | --- | --- |
| Dense retrieval | `Snowflake/snowflake-arctic-embed-xs` int8 | 23 MB ONNX, 384-d | Query prefix applied. Cosine vs fp32 ~0.998 on held-out sentences. |
| Sparse retrieval | `Qdrant/bm25` | tokenizer only | Document vectors are term frequencies; Qdrant applies IDF. Queries use `query_embed`. |
| Rerank | `Xenova/ms-marco-MiniLM-L-6-v2` int8 | 23 MB ONNX | Cross-encoder over the top 12 fused hits. Sigmoid of the logit feeds the trust score. |
| Generation (optional) | any OpenAI-compatible chat model | remote | Default `gpt-4.1-mini`. Groq, Together, OpenRouter, Ollama all work via `LLM_BASE_URL`. |

Embedding inference is serialized behind a lock. Two forward passes at once
on 0.1 CPU only stack activation memory.

To swap models, set `EMBEDDING_MODEL` / `RERANKER_MODEL` to keys in
`backend/app/ml/registry.py`. Collection names include the embedder name and
dimension, so a model change does not mix vector spaces.

## Retrieval pipeline

1. Optional query rewrite (LLM only).
2. Dense search + BM25 search, fused with RRF inside Qdrant.
3. Cross-encoder rerank of the fused list.
4. Top passages go to generation or, with no LLM, are returned as quotes.

Chunking is section-aware and cuts on sentence boundaries, with a trailing
overlap so consecutive chunks share context. PDF cleanup joins hyphenated
line breaks and drops repeating headers.

## API (selected)

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | Postgres, Qdrant, LLM status |
| GET | `/capabilities` | Active models, paper count |
| GET | `/papers` | Library |
| POST | `/ingest/arxiv/search` | arXiv keyword search |
| POST | `/ingest/arxiv` | Background ingest |
| POST | `/chat` | Retrieve, rerank, answer, trust |
| POST | `/integrity/papers/{id}/check` | Citation integrity job |
| GET | `/graph` | Papers, entities, citation edges |
| POST | `/research` | Multi-paper review |
| POST | `/eval/run?suite=retrieval` | Ablation eval |

Interactive docs: `/docs` on the API host.

## Running locally

Needs Python 3.12+, Node 20+, Postgres, Qdrant, and (optional) an LLM key.

```bash
cp backend/.env.example backend/.env   # fill DATABASE_URL, QDRANT_URL, optional LLM_API_KEY

# infra
cd infra && docker compose up -d postgres qdrant

# api
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# ui
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173` (Vite proxies `/api` to `:8000`).

Seed the eval papers and run retrieval ablations:

```bash
cd backend
python scripts/seed_corpus.py
python -m app.eval.eval_runner
```

Unit tests and lint:

```bash
cd backend && ruff check app tests scripts && pytest tests/ -q
cd frontend && npm run build
```

## Deployment

- **Frontend:** Vercel, root `frontend/`. Set `VITE_API_BASE_URL` to the API origin.
- **API:** Render, Docker from `backend/Dockerfile`. The image bakes the ONNX
  weights so a cold start does not download models on first request.
- **Postgres:** Supabase. Use the **session pooler** URI (`postgresql+psycopg://...`)
  because the direct hostname is IPv6-only on the free tier.
- **Vectors:** Qdrant Cloud free cluster.

Render env vars: `DATABASE_URL`, `QDRANT_URL`, `QDRANT_API_KEY`,
`CORS_ORIGINS`, `CORS_ORIGIN_REGEX`, optional `LLM_API_KEY`.

Free Render instances spin down after 15 minutes idle and take about a
minute to wake. Postgres and Qdrant keep the data.

## What this is not

Not a hosted research product. Not a replacement for reading the papers.
The eval set is a seed (10 questions on three well-known papers), enough to
prove the ablation pipeline, not enough to claim SOTA retrieval. Grow
`backend/app/eval/eval_dataset.json` as the library grows.

Measured locally after seeding Attention, BERT, and GPT-3 (paper-id
retrieval, 10 questions):

| Stage | MRR | Hit@5 | nDCG@10 |
| --- | --- | --- | --- |
| Dense only | 1.00 | 1.00 | 1.00 |
| BM25 only | 1.00 | 1.00 | 1.00 |
| Hybrid RRF | 1.00 | 1.00 | 1.00 |
| Hybrid + rerank | 0.95 | 1.00 | 0.96 |

The three papers are easy to tell apart, so first-stage retrieval already
puts the right paper first. The reranker is still the right architecture
for a mixed library; on this seed it slightly reorders one question, which
is why the number is in the table instead of being rounded away.
