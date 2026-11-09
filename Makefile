PYTHON ?= python3

.PHONY: help setup dev backend frontend build start test demo

help:
	@echo "make setup     Install Python and frontend dependencies"
	@echo "make dev       Start API and frontend together on localhost:5173"
	@echo "make build     Build the frontend for the single-server app"
	@echo "make start     Serve the built app at localhost:8000"
	@echo "make test      Backend checks and frontend build"
	@echo "make demo      Add offline sample notes (API must be running)"

setup:
	$(PYTHON) -m venv backend/.venv
	backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
	cd frontend && npm ci

dev:
	$(PYTHON) scripts/dev.py

backend:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev -- --host 127.0.0.1

build:
	cd frontend && npm run build

start:
	cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

test:
	cd backend && .venv/bin/ruff check app tests scripts
	cd backend && .venv/bin/pytest -q
	cd frontend && npm run lint
	cd frontend && npm run build

demo:
	curl --fail --silent --show-error -X POST http://127.0.0.1:8000/api/demo/seed
