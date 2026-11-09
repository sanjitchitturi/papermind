# Architecture

PaperMind is a local research workspace. One FastAPI process serves the API and, after a frontend build, the React application. SQLite stores the library and derived records. There is no hosted vector database, account requirement, or model download in the default runtime.

## Request paths

```text
Browser ── /api/* ── FastAPI ── SQLite
                         │
                         ├── local PDF extraction and BM25 retrieval
                         ├── optional arXiv search/download
                         └── optional OpenAI-compatible language model
```

During development, Vite proxies `/api` to the API on port 8000. A production frontend build is served by FastAPI from `frontend/dist`, including application routes. API documentation is available at `/docs`.

## Data and retrieval

- Ingestion extracts text from PDFs with PyMuPDF, identifies sections, and splits text into overlapping passages with page references.
- Uploaded PDFs are temporary and removed after ingestion; extracted text and page references remain. arXiv downloads are cached in the storage directory. Keep your original PDFs separately if you need them.
- Papers, passages, bibliography entries, entities, answers, feedback, jobs, and evaluation runs live in SQLite. The database enables foreign-key checks, a busy timeout, and write-ahead logging for file-backed storage.
- BM25 ranks passages by lexical overlap with the question. It computes statistics from persisted chunks for each query, so successful additions and deletions are visible without synchronizing a second index.
- A paper filter scopes retrieval. Paper identifiers select resources; they are not access credentials.
- Without a language model, Questions returns matching excerpts and Research groups retrieved evidence. The entity graph uses a small research-term dictionary; it is not a comprehensive scientific knowledge graph.

BM25 is a transparent baseline for a bounded personal library. It can miss synonyms and paraphrases. Corpus size limits protect the local workflow, but this implementation is not intended for a large multi-tenant search service.

## Optional generation

Set `LLM_API_KEY` (or `OPENAI_API_KEY`), plus an optional `LLM_BASE_URL` and `LLM_MODEL`, to enable an OpenAI-compatible provider. The backend owns these settings; the browser does not receive the key. Settings and provider clients are cached per process, so restart after changing credentials.

Provider-backed operations send questions and selected paper text to the configured endpoint. Leave the key empty for a local-only PDF and sample-data workflow. arXiv search/download independently needs internet access. Installing dependencies also needs internet access once.

Generated answers, citation judgments, and contradiction candidates require human review. The evidence score is a heuristic, not a calibrated probability that an answer is correct. A citation judgment from the same class of language model is not independent factual verification.

## Jobs and persistence

Long operations use an in-process worker and store progress in SQLite. Clients poll job status. After a server restart, unfinished jobs are marked failed so they can be retried; the queue does not automatically resume work. Run one application process for this local job model.

The default native data directory is `backend/storage` when launched through the supplied commands. The container uses its configured persistent volume. Back up the database and stored files with the application stopped; do not copy only the main SQLite file while writes are active because WAL files may contain committed data.

## Access boundary

The supplied native server binds to loopback. PaperMind has no user accounts, session cookies, access tokens, ownership checks, or permission roles. Its library is shared by everyone who can reach the API. CORS controls browser access; it does not authenticate clients.

For a public installation, add authentication and authorization at an appropriate boundary before exposing the service. Keep provider credentials in server environment configuration. The current architecture is suitable for a personal workspace or a controlled demonstration.

## Source map

| Area | Source |
| --- | --- |
| Server, API registration, built UI | `backend/app/main.py` |
| Environment settings | `backend/app/core/config.py` |
| Database engine and models | `backend/app/db/` |
| PDF ingestion | `backend/app/ingestion/` |
| BM25 search | `backend/app/retrieval/search.py` |
| Answer generation and citation review | `backend/app/generation/` |
| Research workflow | `backend/app/agent/` |
| Jobs | `backend/app/core/jobs.py` |
| Browser API calls | `frontend/src/api/client.ts` |
