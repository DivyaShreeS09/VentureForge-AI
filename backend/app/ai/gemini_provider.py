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
from app.ai.guardrails import build_prompt
from app.ai.schemas import NarrativeContext, NarrativeEnhancement

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash"
REQUEST_TIMEOUT_SECONDS = 8.0
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        if not api_key:
            raise ValueError("GeminiProvider requires a non-empty api_key")
        self._api_key = api_key
        self._model = model

    def generate_narrative(self, context: NarrativeContext) -> NarrativeEnhancement:
        prompt = build_prompt(context)
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
                        "maxOutputTokens": 1024,
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
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMUnavailable(f"Gemini did not return valid JSON: {exc}") from exc

        try:
            return NarrativeEnhancement.model_validate(payload)
        except ValidationError as exc:
            raise LLMUnavailable(f"Gemini response failed schema validation: {exc}") from exc
