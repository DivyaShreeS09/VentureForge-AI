"""Resolves which LLM provider (if any) is active, based only on GEMINI_API_KEY/GEMINI_MODEL
(see app.core.config.Settings — the same env-var loading every other setting in this app uses).

Returns None whenever GEMINI_API_KEY is not set — the deterministic Judge Agent path never
imports or requires this to return a provider. The API key is never read from a request, never
logged, and never sent to the frontend.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.base import LLMProvider
from app.core.config import settings


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider | None:
    if not settings.gemini_api_key:
        return None

    from app.ai.gemini_provider import GeminiProvider

    return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
