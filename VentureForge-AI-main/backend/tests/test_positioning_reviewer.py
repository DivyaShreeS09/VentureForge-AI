"""Tests for the Gemini positioning reviewer (Phase 0.5): app.ai.gemini_provider.review_positioning
and its never-raising wrapper app.agents.positioning_reviewer.review_positioning_safely.

No live API key is required or used anywhere in this file — every Gemini call is mocked at the
httpx layer, exactly like the existing narrative-layer tests in test_ai_layer.py.
"""

import json

import httpx
import pytest

from app.ai import factory
from app.ai.base import LLMUnavailable
from app.ai.gemini_provider import GeminiProvider
from app.ai.schemas import GeminiPositioningRecommendation, PositioningReviewContext
from app.agents.positioning_reviewer import review_positioning_safely


def _gemini_envelope(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _fake_response(json_body: dict) -> httpx.Response:
    request = httpx.Request("POST", "https://example.invalid")
    return httpx.Response(200, json=json_body, request=request)


@pytest.fixture(autouse=True)
def _clear_provider_cache():
    factory.get_llm_provider.cache_clear()
    yield
    factory.get_llm_provider.cache_clear()


def _context() -> PositioningReviewContext:
    return PositioningReviewContext(
        startup_description="An AI platform for early diabetic-foot risk detection.",
        model_category_label="b2b",
        model_category_confidence=0.32,
        model_category_is_uncertain=True,
        taxonomy_candidate_domains=["HealthTech Diagnostics", "Clinical Decision Support"],
    )


# --- GeminiProvider.review_positioning: schema/HTTP failure modes ------------------------------


def test_valid_response_is_accepted(monkeypatch):
    payload = {
        "recommended_primary_domain": "HealthTech Diagnostics",
        "recommended_secondary_domains": ["Clinical Decision Support"],
        "confidence": 0.7,
        "rationale": "The description centers on diagnostic detection, not general AI tooling.",
    }
    response = _fake_response(_gemini_envelope(json.dumps(payload)))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    result = provider.review_positioning(_context())

    assert isinstance(result, GeminiPositioningRecommendation)
    assert result.recommended_primary_domain == "HealthTech Diagnostics"
    assert result.confidence == 0.7


def test_invalid_enum_domain_is_rejected(monkeypatch):
    payload = {
        "recommended_primary_domain": "Not A Real Taxonomy Domain",
        "recommended_secondary_domains": [],
        "confidence": 0.7,
        "rationale": "x",
    }
    response = _fake_response(_gemini_envelope(json.dumps(payload)))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.review_positioning(_context())


def test_invalid_secondary_enum_domain_is_rejected(monkeypatch):
    payload = {
        "recommended_primary_domain": "HealthTech Diagnostics",
        "recommended_secondary_domains": ["Not A Real Domain"],
        "confidence": 0.7,
        "rationale": "x",
    }
    response = _fake_response(_gemini_envelope(json.dumps(payload)))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.review_positioning(_context())


def test_malformed_json_is_rejected(monkeypatch):
    response = _fake_response(_gemini_envelope("not valid json{{"))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.review_positioning(_context())


def test_timeout_raises_llm_unavailable(monkeypatch):
    def _raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", _raise_timeout)
    provider = GeminiProvider(api_key="test-key")

    with pytest.raises(LLMUnavailable):
        provider.review_positioning(_context())


def test_confidence_out_of_range_is_rejected(monkeypatch):
    payload = {
        "recommended_primary_domain": "HealthTech Diagnostics",
        "recommended_secondary_domains": [],
        "confidence": 1.5,
        "rationale": "x",
    }
    response = _fake_response(_gemini_envelope(json.dumps(payload)))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.review_positioning(_context())


def test_empty_recommendation_missing_required_field_is_rejected(monkeypatch):
    response = _fake_response(_gemini_envelope(json.dumps({})))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.review_positioning(_context())


def test_secondary_domains_bounded_to_three():
    rec = GeminiPositioningRecommendation(
        recommended_primary_domain="HealthTech Diagnostics",
        recommended_secondary_domains=[
            "Clinical Decision Support", "Remote Patient Monitoring", "Enterprise AI", "EdTech",
        ],
        confidence=0.5,
        rationale="x",
    )
    assert len(rec.recommended_secondary_domains) == 3


# --- review_positioning_safely: never raises, always degrades to None --------------------------


def test_unavailable_api_key_returns_none_without_raising(monkeypatch):
    monkeypatch.setattr("app.ai.factory.settings.gemini_api_key", None)
    result = review_positioning_safely("desc", {"label": "b2b", "confidence": 0.3, "is_uncertain": True}, [])
    assert result is None


def test_provider_llm_unavailable_returns_none(monkeypatch):
    class _FailingProvider:
        def review_positioning(self, context):
            raise LLMUnavailable("simulated failure")

    monkeypatch.setattr("app.agents.positioning_reviewer.get_llm_provider", lambda: _FailingProvider())
    result = review_positioning_safely("desc", {"label": "b2b", "confidence": 0.3, "is_uncertain": True}, [])
    assert result is None


def test_unexpected_exception_returns_none_not_raised(monkeypatch):
    class _CrashingProvider:
        def review_positioning(self, context):
            raise RuntimeError("boom")

    monkeypatch.setattr("app.agents.positioning_reviewer.get_llm_provider", lambda: _CrashingProvider())
    result = review_positioning_safely("desc", {"label": "b2b", "confidence": 0.3, "is_uncertain": True}, [])
    assert result is None


def test_successful_review_is_returned_through_the_safe_wrapper(monkeypatch):
    valid = GeminiPositioningRecommendation(
        recommended_primary_domain="HealthTech Diagnostics", confidence=0.6, rationale="ok"
    )

    class _WorkingProvider:
        def review_positioning(self, context):
            return valid

    monkeypatch.setattr("app.agents.positioning_reviewer.get_llm_provider", lambda: _WorkingProvider())
    result = review_positioning_safely("desc", {"label": "b2b", "confidence": 0.3, "is_uncertain": True}, [])
    assert result is valid
