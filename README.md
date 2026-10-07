# PaperMind

A retrieval system for research papers that does more than chat with a PDF.

**Live app:** [thepapermind.vercel.app](https://thepapermind.vercel.app)
**API:** [papermind-api-laof.onrender.com/docs](https://papermind-api-laof.onrender.com/docs)
**Source:** [github.com/sanjitchitturi/papermind](https://github.com/sanjitchitturi/papermind)

Dense retrieval and BM25 run on local int8 ONNX models. A MiniLM cross-encoder
is in the stack and is measured locally; the live API leaves it off so the
process fits in 512 MB. Generation, citation integrity, and research mode use
any OpenAI-compatible API. If that call fails, or no key is set, chat still
returns the ranked passages as quotes.

---

## Why this exists

Most RAG-for-papers projects stop at: chunk a PDF, embed it, answer with
citations. That is necessary, and it is also what ChatPDF, SciSpace, and a
dozen GitHub demos already do. PaperMind keeps that core and adds the pieces
those tools typically skip.

1. **Hybrid retrieval with a measured reranker.** Dense + BM25 fused with
   reciprocal rank fusion, then an optional cross-encoder over the fused
   candidates. The eval dashboard reports dense, sparse, hybrid, and
   hybrid+rerank as separate ablations. The live service reports the first
   three, because the reranker is off there.
2. **Citation integrity.** For each in-text citation, extract the claim
   attributed to the cited work, retrieve a passage from that work if it is
   in the library, and judge support. Unresolved citations stay unresolved.
3. **Trust scores that can abstain.** Retrieval margin, reranker
   confidence, citation pass rate, and self-consistency combine into a 0-100
   score. Below a threshold the system says it is not confident.
4. **A knowledge graph that is not decorative.** Entities are extracted at
   ingest and citation edges resolve to other papers in the library by
   arXiv id or title.
5. **An agentic research mode with a visible trace.** Broad questions are
   decomposed, retrieved across papers, critiqued for coverage, then
   synthesized into a review plus a comparison table.

This is a capstone-style ML systems project: the interesting work is the
retrieval stack, the evals, and the failure modes, not a chat wrapper.

---

## Architecture

```
PDF / arXiv
    -> parse, clean, section-aware sentence chunks
    -> local dense encoder + BM25 sparse vectors
    -> Qdrant (RRF fusion)
    -> optional MiniLM cross-encoder rerank
    -> extractive quotes, or LLM generation + citation verify + trust
Postgres holds papers, chunks, claims, citation checks, entities,
paper_entities, paper_citations, jobs, answers, eval_runs.
```

```
frontend (Vite, React, Tailwind)
        |
        |  REST + job polling
        v
backend (FastAPI)
  ingest  ->  jobs (1 worker)  ->  pipeline
  chat    ->  hybrid_search    ->  generate / extract
  integrity / research / graph / eval
        |
        +--> Postgres (Supabase session pooler)
        +--> Qdrant Cloud (named collection per embedder+dim)
        +--> local ONNX (fastembed + onnxruntime)
```

Stack: FastAPI, SQLModel, Alembic, Postgres, Qdrant, fastembed/onnxruntime,
React, Vite, Tailwind. Frontend on Vercel. API on Render (Docker, 512 MB).

---

## Models

Weights are int8. Embedding inference is serialized and runs one chunk at a
time. Two ONNX sessions do not fit next to FastAPI on Render's free plan
(512 MB), so production sets `LOW_MEMORY=true`, which forces
`RERANKER_MODEL=none`.

| Role | Model | Size | Where it runs |
| --- | --- | --- | --- |
| Dense retrieval | `Snowflake/snowflake-arctic-embed-xs` int8 | 23 MB ONNX, 384-d | Always. Query prefix applied. Cosine vs fp32 ~0.998. |
| Sparse retrieval | `Qdrant/bm25` | tokenizer only | Always. Documents store term frequencies; Qdrant applies IDF. Queries use `query_embed`. |
| Rerank | `Xenova/ms-marco-MiniLM-L-6-v2` int8 | 23 MB ONNX | Local and larger hosts. Off on the live API. |
| Generation | OpenAI-compatible chat | remote | Default `gpt-4o-mini`. Groq, Together, OpenRouter, and Ollama work via `LLM_BASE_URL`. |

The live API currently serves Arctic Embed XS, BM25, no reranker, and
`gpt-4o-mini` when the provider accepts the request. A quota or auth failure
on chat falls back to extractive quotes instead of a 500. Integrity and
research mode still require a working generation call.

To swap models, set `EMBEDDING_MODEL` / `RERANKER_MODEL` to keys in
`backend/app/ml/registry.py`. Collection names include the embedder name and
dimension, so a model change does not mix vector spaces.

The Docker image bakes the ONNX weights at build time so a cold start does
not download models on the first request.

---

## Retrieval pipeline

1. Optional query rewrite (LLM only; skipped when generation is unavailable).
2. Dense search + BM25 search, fused with RRF inside Qdrant.
3. Cross-encoder rerank of the fused list, when a reranker is loaded.
4. Top passages go to generation, or are returned as quotes.
5. Citation verification (generative mode) and trust scoring.

Chunking is section-aware and cuts on sentence boundaries, with a trailing
overlap so consecutive chunks share context. PDF cleanup joins hyphenated
line breaks and drops repeating headers.

Dedupe: the same arXiv id is not ingested twice. Bibliography entries are
linked to other library papers by arXiv id first, then by normalized title.

---

## Trust score

The 0-100 score is a weighted combination of:

- **Retrieval margin:** gap between the top hit and the next distinct paper.
- **Rerank confidence:** sigmoid of the MiniLM logit on the top passage.
  Neutral (0.5) when the reranker is off.
- **Citation pass rate:** share of generated citations that verify against
  retrieved text (1.0 in extractive mode, because the answer *is* the text).
- **Self-consistency:** agreement across a second sampled generation when an
  LLM is configured.

Below a threshold the API sets `abstained: true` and the UI labels the
answer as abstained instead of presenting fluent uncertainty as fact.

---

## Eval

The harness in `backend/app/eval/` scores retrieval as four ablations on
the same questions: dense only, BM25 only, hybrid RRF, then hybrid plus the
cross-encoder. Metrics: MRR, Hit@5, nDCG@10. Generation eval is a separate
suite and needs an LLM key.

Measured locally after seeding Attention (`1706.03762`), BERT (`1810.04805`),
and GPT-3 (`2005.14165`). Paper-id retrieval, 10 questions:

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

The same 10 questions, run on the live API with the reranker off (commit
`975a88d`): dense, BM25, and hybrid RRF are all MRR 1.00, Hit@5 1.00,
nDCG@10 1.00. That run has no hybrid+rerank row, because the model is not
loaded.

Grow `backend/app/eval/eval_dataset.json` as the library grows. Trigger a
run from `/eval` or:

```bash
cd backend && python -m app.eval.eval_runner
```

---

## API (selected)

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | Postgres, Qdrant, LLM status |
| GET | `/capabilities` | Active models, paper count, chunk count |
| GET | `/papers` | Library |
| DELETE | `/papers/{id}` | Remove a paper and its vectors |
| POST | `/ingest/arxiv/search` | arXiv keyword search |
| POST | `/ingest/arxiv` | Background ingest by arXiv id |
| POST | `/ingest/upload` | PDF upload |
| GET | `/ingest/jobs/{id}` | Job status |
| POST | `/chat` | Retrieve, rerank, answer, trust |
| POST | `/integrity/papers/{id}/check` | Citation integrity job |
| GET | `/integrity/papers/{id}/report` | Stored integrity report |
| GET | `/graph` | Papers, entities, citation edges |
| POST | `/research` | Multi-paper review |
| POST | `/eval/run?suite=retrieval` | Ablation eval |
| GET | `/eval/history` | Past eval runs |
| POST | `/feedback` | Thumbs on an answer |

Interactive docs: `/docs` on the API host. Rate limits apply on ingest and
chat.

---

## Repository layout

```
backend/app/
  api/           FastAPI routers
  core/          config, jobs, LLM client, vector store
  db/            SQLModel models, session
  ingestion/     PDF parse, cleanup, chunking, bib, pipeline
  ml/            ONNX registry, embedder, reranker
  retrieval/     hybrid search, RRF
  generation/    cited generation + extractive fallback
  integrity/     citation checks, contradictions
  graph/         entity extraction, graph export
  agent/         research-mode planner
  eval/          dataset + ablation runner
  trust/         score + abstention
backend/migrations/   Alembic, single initial revision
backend/tests/
frontend/src/    React pages and the monochrome design system
infra/           local docker-compose (Postgres + Qdrant)
```

---

## Running locally

Needs Python 3.12+, Node 20+, Postgres, Qdrant, and (optional) an LLM key.

```bash
cp backend/.env.example backend/.env
# fill DATABASE_URL, QDRANT_URL, optional LLM_API_KEY / OPENAI_API_KEY

cd infra && docker compose up -d postgres qdrant

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173` (Vite proxies `/api` to `:8000`).

Seed the eval papers and run retrieval ablations:

```bash
make seed
make eval
```

Unit tests and lint:

```bash
make test
```

`LLM_API_KEY` may be left empty. `OPENAI_API_KEY` is accepted as an alias.
`LLM_BASE_URL` points at Groq, Together, OpenRouter, or a local Ollama.

---

## Deployment

- **Frontend:** Vercel, root `frontend/`. Production: [thepapermind.vercel.app](https://thepapermind.vercel.app). Set `VITE_API_BASE_URL` to the API origin.
- **API:** Render, Docker from `backend/Dockerfile`. Free plan, 512 MB.
- **Postgres:** Supabase. Use the **session pooler** URI
  (`postgresql+psycopg://postgres.<ref>:...@aws-0-....pooler.supabase.com:5432/postgres`).
  The direct `db.<ref>.supabase.co` hostname is IPv6-only on the free tier
  and Render cannot reach it.
- **Vectors:** Qdrant Cloud free cluster. Set `QDRANT_URL` and `QDRANT_API_KEY`.

Render env vars:

```
DATABASE_URL
QDRANT_URL
QDRANT_API_KEY
CORS_ORIGINS=["https://thepapermind.vercel.app"]
CORS_ORIGIN_REGEX=https://.*\.vercel\.app
EMBEDDING_MODEL=arctic-embed-xs-int8
RERANKER_MODEL=none
LOW_MEMORY=true
ML_BATCH_SIZE=1
MODEL_CACHE_DIR=/app/.models
LLM_API_KEY          # optional; needs a funded account
LLM_MODEL=gpt-4o-mini
```

Blueprint: `render.yaml`. Migrations run on API startup. Interrupted jobs
are marked failed on restart.

Free Render instances spin down after 15 minutes idle and take about a
minute to wake. Postgres and Qdrant keep the data. The first request after
sleep is slow; `/health` is the right warmup.

---

## Design constraints (intentional)

- No hosted embedding API in the default path. The capstone has to run
  without a paid key.
- One job worker. Render free is 0.1 CPU; parallel ONNX is a memory
  regression, not a speedup.
- One ONNX session on the free API. The reranker stays in the code and in
  the local eval table. Production does not load it.
- Honest evals. A seed of three famous papers is too easy for first-stage
  retrieval. The table reports the rerank drop instead of hiding it.
- Monochrome UI. The product is a research tool, not a dashboard template.

---

## What this is not

Not a hosted research product. Not a replacement for reading the papers.
The eval set is a seed (10 questions on three well-known papers), enough to
prove the ablation pipeline, not enough to claim SOTA retrieval.

Integrity and research mode require a working LLM call. Chat does not: with
no key, or when the provider rejects the request, the answer is the ranked
passages.

---

## License

MIT. See [LICENSE](LICENSE).
