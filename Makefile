.PHONY: backend frontend test seed eval help infra

help:
	@echo "make infra     postgres + qdrant"
	@echo "make backend   uvicorn --reload"
	@echo "make frontend  vite dev"
	@echo "make test      ruff + pytest + frontend build"
	@echo "make seed      ingest Attention, BERT, and GPT-3"
	@echo "make eval      retrieval ablations"

infra:
	cd infra && docker compose up -d postgres qdrant

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/ruff check app tests scripts
	cd backend && .venv/bin/pytest tests/ -q
	cd frontend && npm run build

seed:
	cd backend && .venv/bin/python scripts/seed_corpus.py

eval:
	cd backend && .venv/bin/python -m app.eval.eval_runner
