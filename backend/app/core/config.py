"""
Central place for environment-driven settings. Everything that differs
between local dev, CI, and the deployed environment should be read here
instead of being hardcoded in individual modules.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres (Supabase in prod, local container in dev)
    # psycopg3 driver, hence "postgresql+psycopg" rather than plain "postgresql"
    database_url: str = "postgresql+psycopg://papermind:papermind@localhost:5432/papermind"

    # Qdrant (Qdrant Cloud in prod, local container in dev)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "paper_chunks"

    # OpenAI
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    generation_model: str = "gpt-4o-mini"
    judge_model: str = "gpt-4o-mini"

    # Retrieval tuning
    retrieval_top_k: int = 20
    rerank_top_n: int = 6
    chunk_target_tokens: int = 400
    chunk_overlap_tokens: int = 60

    # Trust score thresholds
    trust_abstain_threshold: int = 45

    # Misc
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    # lru_cache means we only read the environment once per process,
    # not on every single request.
    return Settings()
