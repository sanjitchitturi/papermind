"""
Small wrapper around the OpenAI client. Everything that talks to an LLM
goes through here so retry/backoff and model selection stay in one place
instead of being copy-pasted into every module that needs a completion.
"""

import json

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

settings = get_settings()
_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def embed(texts: list[str]) -> list[list[float]]:
    # Batched on purpose, embedding one-by-one during ingestion would be
    # needlessly slow and burn through rate limits for no reason.
    response = get_client().embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in response.data]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def chat(messages: list[dict], model: str | None = None, temperature: float = 0.2) -> str:
    response = get_client().chat.completions.create(
        model=model or settings.generation_model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def chat_json(messages: list[dict], model: str | None = None, temperature: float = 0.0) -> dict:
    """
    Asks the model to return JSON and parses it. Used for structured
    extraction (claims, entities, eval judgments) where we need a reliable
    shape back, not free text we then have to regex apart.
    """
    response = get_client().chat.completions.create(
        model=model or settings.judge_model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Better to surface an empty result than crash the whole pipeline
        # over one malformed response from the model.
        return {}
