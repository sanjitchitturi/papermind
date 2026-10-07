"""
Central place for environment-driven settings. Everything that differs
between local dev, CI, and the deployed environment is read here instead
of being hardcoded in individual modules.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=("settings_",))

    environment: Literal["development", "production", "test"] = "development"
    app_version: str = "1.0.0"
    git_commit_sha: str = Field("local", validation_alias=AliasChoices("GIT_COMMIT_SHA", "RENDER_GIT_COMMIT"))

    # Postgres. psycopg3 driver, hence "postgresql+psycopg" rather than plain "postgresql".
    database_url: str = "postgresql+psycopg://papermind:papermind@localhost:5432/papermind"

    # Qdrant. ":memory:" runs an in-process instance, which the tests use.
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_prefix: str = "papermind"

    # Local ONNX models served through fastembed. Keys refer to the registry
    # in app/ml/registry.py. An empty reranker disables cross-encoder reranking.
    embedding_model: str = "arctic-embed-xs-int8"
    reranker_model: str = "ms-marco-minilm-l6-int8"
    model_cache_dir: str = "./.models"
    ml_threads: int = 1
    ml_batch_size: int = 4
    # Render free is 512 MB. Two ONNX sessions on top of FastAPI will get
    # the process killed. Production defaults to embedder-only unless this
    # is set false on a larger box.
    low_memory: bool | None = None

    # Any OpenAI-compatible chat endpoint works here: OpenAI, Groq, Together,
    # OpenRouter, Gemini's compatibility layer, a local Ollama or vLLM server.
    # OPENAI_API_KEY is accepted as an alias so existing setups keep working.
    llm_api_key: str = Field("", validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"))
    llm_base_url: str | None = None
    llm_model: str = "gpt-4.1-mini"
    llm_judge_model: str | None = None
    llm_timeout_seconds: float = 60.0

    # Retrieval
    retrieval_candidates: int = 24
    rerank_candidates: int = 12
    context_passages: int = 6
    chunk_target_tokens: int = 300
    chunk_overlap_tokens: int = 50

    # Trust score
    trust_abstain_threshold: int = 45
    trust_self_consistency: bool = True

    # Guard rails for a public deployment on small hardware
    max_upload_mb: int = 25
    max_pdf_pages: int = 50
    max_papers: int = 150
    allow_deletes: bool = True
    rate_limit_enabled: bool = True
    jobs_inline: bool = False  # run background jobs synchronously, used by tests

    cors_origins: list[str] = ["http://localhost:5173"]
    cors_origin_regex: str | None = None
    storage_dir: str = "./storage"

    @model_validator(mode="after")
    def _fit_small_instances(self):
        constrained = self.low_memory if self.low_memory is not None else self.environment == "production"
        if constrained:
            self.ml_batch_size = min(self.ml_batch_size, 1)
            self.ml_threads = 1
            self.reranker_model = "none"
        return self

    @property
    def llm_configured(self) -> bool:
        key = self.llm_api_key.strip()
        return bool(key) and "placeholder" not in key.lower()

    @property
    def judge_model(self) -> str:
        return self.llm_judge_model or self.llm_model


@lru_cache
def get_settings() -> Settings:
    # Read the environment once per process, not on every request.
    return Settings()
