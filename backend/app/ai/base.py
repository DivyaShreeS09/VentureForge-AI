"""Provider-neutral interface for the optional LLM narrative layer.

Any provider (Gemini today; other hosted or local models later, if ever added) implements this Protocol.
Nothing outside `backend/app/ai/` imports a specific provider — callers only ever see
`LLMProvider` and go through `backend/app/ai/factory.py` to get one (or None).
"""

from __future__ import annotations

from typing import Protocol

from app.ai.schemas import NarrativeContext, NarrativeEnhancement


class LLMUnavailable(RuntimeError):
    """Raised by any provider for every failure mode: missing/invalid key, timeout, rate limit,
    network error, malformed JSON, or a response that fails schema validation. Callers only ever
    need to catch this one exception type to fall back to the deterministic path."""


class LLMProvider(Protocol):
    def generate_narrative(self, context: NarrativeContext) -> NarrativeEnhancement:
        """Return a validated narrative enhancement, or raise LLMUnavailable."""
        ...
