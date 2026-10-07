"""
Provider-agnostic LLM client. Anything that speaks the OpenAI chat
completions API works: OpenAI itself, Groq, Together, OpenRouter, Gemini's
compatibility endpoint, or a local Ollama/vLLM server. Every LLM call in
the codebase goes through here so retries, timeouts, JSON parsing and
model quirks are handled in one place.

When no API key is configured the rest of the system degrades instead of
failing: retrieval and reranking still run locally, chat falls back to an
extractive answer, and LLM-only features raise LLMUnavailable, which the
API turns into a clear 503.
"""

import json
import logging
import re
import threading
from urllib.parse import urlparse

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None
_client_lock = threading.Lock()

_TRANSIENT = (APIConnectionError, APITimeoutError, InternalServerError)

# Reasoning models reject custom temperatures and use max_completion_tokens.
_REASONING_MODEL = re.compile(r"^(o\d|gpt-5)", re.IGNORECASE)


class LLMUnavailable(RuntimeError):
    """No LLM is configured, so features that need generation can't run."""


class LLMProviderError(RuntimeError):
    """The provider rejected the request in a way retrying won't fix (bad key, no access)."""


def llm_available() -> bool:
    return get_settings().llm_configured


def provider_host() -> str:
    base = get_settings().llm_base_url
    return urlparse(base).hostname or base if base else "api.openai.com"


def get_client() -> OpenAI:
    global _client
    if not llm_available():
        raise LLMUnavailable("No LLM API key is configured. Set LLM_API_KEY to enable generation features.")
    if _client is None:
        with _client_lock:
            if _client is None:
                settings = get_settings()
                _client = OpenAI(
                    api_key=settings.llm_api_key,
                    base_url=settings.llm_base_url or None,
                    timeout=settings.llm_timeout_seconds,
                    max_retries=0,  # tenacity owns retries so backoff is consistent
                )
    return _client


def reset_client() -> None:
    global _client
    _client = None


def _completion_kwargs(model: str, temperature: float | None, max_tokens: int | None) -> dict:
    kwargs: dict = {"model": model}
    if _REASONING_MODEL.match(model):
        if max_tokens:
            kwargs["max_completion_tokens"] = max_tokens
    else:
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
    return kwargs


@retry(
    retry=retry_if_exception_type(_TRANSIENT),
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=8),
    reraise=True,
)
def _create(messages: list[dict], json_mode: bool, **kwargs) -> str:
    try:
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = get_client().chat.completions.create(messages=messages, **kwargs)
    except (AuthenticationError, PermissionDeniedError, RateLimitError, NotFoundError, BadRequestError) as exc:
        raise LLMProviderError(f"The LLM provider rejected the request: {exc.message}") from exc
    return response.choices[0].message.content or ""


def chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float | None = 0.2,
    max_tokens: int | None = None,
    system: str | None = None,
) -> str:
    settings = get_settings()
    if system:
        messages = [{"role": "system", "content": system}, *messages]
    return _create(messages, json_mode=False, **_completion_kwargs(model or settings.llm_model, temperature, max_tokens))


def chat_json(
    messages: list[dict],
    model: str | None = None,
    temperature: float | None = 0.0,
    system: str | None = None,
) -> dict:
    """
    Asks for a JSON object and parses it. Used for structured extraction
    (claims, entities, verdicts) where a reliable shape matters more than
    prose. Some providers ignore response_format or wrap the JSON in a
    markdown fence, so parsing is deliberately forgiving.
    """
    settings = get_settings()
    system_prompt = (system + "\n\n" if system else "") + "Respond with a single valid JSON object and nothing else."
    full = [{"role": "system", "content": system_prompt}, *messages]
    kwargs = _completion_kwargs(model or settings.judge_model, temperature, None)
    try:
        content = _create(full, json_mode=True, **kwargs)
    except LLMProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        # A provider that doesn't support response_format returns a 400.
        # Retry once without it before giving up on structured output.
        logger.warning("json mode request failed (%s), retrying without response_format", exc)
        content = _create(full, json_mode=False, **kwargs)
    return parse_json_object(content)


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json_object(content: str) -> dict:
    text = _FENCE.sub("", content.strip())
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"items": parsed}
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass
    logger.warning("could not parse JSON from model output: %.200s", content)
    return {}
