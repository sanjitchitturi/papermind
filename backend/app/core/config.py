"""Environment configuration. The default installation needs no remote accounts."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "[::1]", "testserver"]
    max_extracted_chars: int = Field(2_000_000, ge=1000, le=20_000_000)
    environment: Literal["development", "production", "test"] = "development"
    app_version: str = "2.0.0"
    git_commit_sha: str = "local"
    database_url: str = "sqlite:///./storage/papermind.db"
    storage_dir: str = "./storage"
    llm_api_key: str = Field("", validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"), repr=False)
    llm_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_judge_model: str | None = None
    llm_timeout_seconds: float = Field(30.0, gt=0, le=300)
    retrieval_candidates: int = Field(24, ge=1, le=100)
    context_passages: int = Field(6, ge=1, le=20)
    chunk_target_tokens: int = Field(300, ge=50, le=2000)
    chunk_overlap_tokens: int = Field(50, ge=0, le=100)
    trust_abstain_threshold: int = Field(45, ge=0, le=100)
    trust_self_consistency: bool = False
    max_upload_mb: int = Field(25, ge=1, le=100)
    max_pdf_pages: int = Field(50, ge=1, le=500)
    max_papers: int = Field(150, ge=1, le=10000)
    allow_deletes: bool = True
    rate_limit_enabled: bool = True
    jobs_inline: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def llm_configured(self) -> bool:
        key = self.llm_api_key.strip()
        return bool(key) and "placeholder" not in key.lower()

    @property
    def judge_model(self) -> str:
        return self.llm_judge_model or self.llm_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
