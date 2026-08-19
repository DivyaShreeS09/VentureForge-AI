"""Gemini implementation of LLMProvider. Only imported by factory.py when GEMINI_API_KEY is set —
the rest of the app never imports this module directly, so a missing `httpx` or API outage cannot
affect any request path that doesn't opt into the LLM layer.
"""

from __future__ import annotations

import json
import logging

import httpx
from pydantic import ValidationError

from app.ai.base import LLMUnavailable
from app.ai.guardrails import (
    build_competitor_possibilities_prompt,
    build_idea_expansion_prompt,
    build_mentor_prompt,
    build_positioning_prompt,
    build_prompt,
    build_strategic_opportunity_prompt,
)
from app.ai.schemas import (
    CompetitorPossibilitiesContext,
    GeminiCompetitorPossibilities,
    GeminiIdeaExpansion,
    GeminiMentorAdvice,
    GeminiPositioningRecommendation,
    GeminiStrategicOpportunity,
    IdeaExpansionContext,
    MentorContext,
    NarrativeContext,
    NarrativeEnhancement,
    PositioningReviewContext,
    StrategicOpportunityContext,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-flash-latest"
# Product Intelligence Sprint — live-testing against a real key surfaced two silent-failure bugs
# that made every Gemini call fall back to the deterministic path far more often than intended:
# (1) `gemini-2.0-flash`'s free tier returns 429 RESOURCE_EXHAUSTED (limit: 0) on at least one real
# project — `gemini-flash-latest` is the confirmed-working default. (2) newer Gemini models spend a
# variable, often substantial number of tokens "thinking" before emitting the actual JSON answer
# (observed: 1605 thinking tokens for one real mentor-advice prompt) — the old 1024-token budget
# left zero room for the answer itself, truncating it before any JSON content, so every call
# silently raised LLMUnavailable and fell back. `thinkingConfig.thinkingBudget=0` is NOT a fix —
# this model rejects it with a 400 (thinking cannot be fully disabled). Raising the budget is the
# correct fix. REQUEST_TIMEOUT_SECONDS was similarly too tight — measured real-world latency for a
# realistic mentor prompt was 6.9s-10.4s across 3 runs, so the old 8.0s timeout was failing roughly
# as often as it succeeded.
REQUEST_TIMEOUT_SECONDS = 25.0
MAX_OUTPUT_TOKENS = 8192
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        if not api_key:
            raise ValueError("GeminiProvider requires a non-empty api_key")
        self._api_key = api_key
        self._model = model

    def _call(self, prompt: str) -> dict:
        """Shared request/response plumbing for every structured-JSON Gemini call this provider
        makes. Raises LLMUnavailable for every failure mode (timeout, HTTP error, malformed
        response shape, non-JSON text) — callers only need to additionally validate the parsed
        payload against their own expected schema.
        """
        url = f"{API_BASE_URL}/{self._model}:generateContent"
        try:
            response = httpx.post(
                url,
                params={"key": self._api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.3,
                        "maxOutputTokens": MAX_OUTPUT_TOKENS,
                    },
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMUnavailable("Gemini request timed out") from exc
        except httpx.HTTPStatusError as exc:
            # Never surface the raw response body — it can echo back the request (which included
            # the API key as a query param) in error payloads for some failure modes.
            raise LLMUnavailable(f"Gemini returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"Gemini request failed: {type(exc).__name__}") from exc

        try:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMUnavailable(f"Gemini response had unexpected shape: {exc}") from exc

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMUnavailable(f"Gemini did not return valid JSON: {exc}") from exc

    def generate_narrative(self, context: NarrativeContext) -> NarrativeEnhancement:
        payload = self._call(build_prompt(context))
        try:
            return NarrativeEnhancement.model_validate(payload)
        except ValidationError as exc:
            raise LLMUnavailable(f"Gemini response failed schema validation: {exc}") from exc

    def review_positioning(self, context: PositioningReviewContext) -> GeminiPositioningRecommendation:
        payload = self._call(build_positioning_prompt(context))
        try:
            return GeminiPositioningRecommendation.model_validate(payload)
        except ValidationError as exc:
            raise LLMUnavailable(f"Gemini positioning response failed schema validation: {exc}") from exc

    def suggest_competitor_possibilities(
        self, context: CompetitorPossibilitiesContext
    ) -> GeminiCompetitorPossibilities:
        payload = self._call(build_competitor_possibilities_prompt(context))
        try:
            return GeminiCompetitorPossibilities.model_validate(payload)
        except ValidationError as exc:
            raise LLMUnavailable(f"Gemini competitor-possibilities response failed schema validation: {exc}") from exc

    def generate_mentor_advice(self, context: MentorContext) -> GeminiMentorAdvice:
        payload = self._call(build_mentor_prompt(context))
        try:
            return GeminiMentorAdvice.model_validate(payload)
        except ValidationError as exc:
            raise LLMUnavailable(f"Gemini mentor advice response failed schema validation: {exc}") from exc

    def generate_idea_expansion(self, context: IdeaExpansionContext) -> GeminiIdeaExpansion:
        payload = self._call(build_idea_expansion_prompt(context))
        try:
            return GeminiIdeaExpansion.model_validate(payload)
        except ValidationError as exc:
            raise LLMUnavailable(f"Gemini idea expansion response failed schema validation: {exc}") from exc

    def generate_strategic_opportunity(self, context: StrategicOpportunityContext) -> GeminiStrategicOpportunity:
        payload = self._call(build_strategic_opportunity_prompt(context))
        try:
            return GeminiStrategicOpportunity.model_validate(payload)
        except ValidationError as exc:
            raise LLMUnavailable(f"Gemini strategic opportunity response failed schema validation: {exc}") from exc
