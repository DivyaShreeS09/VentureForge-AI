"""Tests for the optional, provider-neutral LLM narrative layer (backend/app/ai/).

These never make a real network call — Gemini is mocked throughout. The one thing every test
here proves collectively: the deterministic pipeline works identically whether or not an LLM is
configured, and every LLM failure mode degrades to None rather than raising.
"""

import json

import httpx
import pytest

from app.ai import factory
from app.ai.base import LLMUnavailable
from app.ai.gemini_provider import GeminiProvider
from app.ai.schemas import NarrativeContext, NarrativeEnhancement


def _gemini_envelope(text: str) -> dict:
    """Wrap raw model output text in the same shape Gemini's REST API returns."""
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


@pytest.fixture(autouse=True)
def _clear_provider_cache():
    factory.get_llm_provider.cache_clear()
    yield
    factory.get_llm_provider.cache_clear()


def _context() -> NarrativeContext:
    return NarrativeContext(
        startup_name="Nova Health",
        startup_description="A telehealth platform for chronic care follow-up.",
        predicted_industry="healthcare",
        industry_confidence=0.9,
        industry_is_uncertain=False,
        funding_score=45,
        funding_level="developing",
        strengths=["Problem Clarity: Specific, well-defined problem"],
        weaknesses=[],
        missing_evidence=["Traction"],
    )


def test_factory_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr("app.ai.factory.settings.gemini_api_key", None)
    assert factory.get_llm_provider() is None


def test_factory_returns_provider_when_key_configured(monkeypatch):
    monkeypatch.setattr("app.ai.factory.settings.gemini_api_key", "test-key")
    provider = factory.get_llm_provider()
    assert isinstance(provider, GeminiProvider)


def _fake_response(json_body: dict) -> httpx.Response:
    request = httpx.Request("POST", "https://example.invalid")
    return httpx.Response(200, json=json_body, request=request)


def test_generate_narrative_success(monkeypatch):
    valid_payload = {
        "executive_summary": "A promising early-stage telehealth startup.",
        "strategic_observations": ["Clear problem statement."],
        "strengths": ["Well-defined problem"],
        "weaknesses": ["No traction yet"],
        "recommendations": ["Recruit pilot users"],
    }
    response = _fake_response(_gemini_envelope(json.dumps(valid_payload)))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    result = provider.generate_narrative(_context())

    assert isinstance(result, NarrativeEnhancement)
    assert result.executive_summary == valid_payload["executive_summary"]


def test_generate_narrative_times_out(monkeypatch):
    def _raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", _raise_timeout)
    provider = GeminiProvider(api_key="test-key")

    with pytest.raises(LLMUnavailable):
        provider.generate_narrative(_context())


def test_generate_narrative_rejects_invalid_json(monkeypatch):
    response = _fake_response(_gemini_envelope("not valid json{{"))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.generate_narrative(_context())


def test_generate_narrative_rejects_schema_violation(monkeypatch):
    # Missing the required executive_summary field entirely.
    malformed_payload = {"strengths": ["ok"]}
    response = _fake_response(_gemini_envelope(json.dumps(malformed_payload)))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.generate_narrative(_context())


def test_generate_narrative_rejects_unexpected_response_shape(monkeypatch):
    response = _fake_response({"unexpected": "shape"})
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.generate_narrative(_context())


def test_narrative_enhancement_bounds_oversized_lists():
    payload = {
        "executive_summary": "x" * 10,
        "strategic_observations": [f"item {i}" for i in range(20)],
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
    }
    result = NarrativeEnhancement.model_validate(payload)
    assert len(result.strategic_observations) <= 6


def test_orchestrator_falls_back_when_provider_unavailable(monkeypatch):
    """The judge node must never fail or block just because an LLM call fails."""
    from app.agents.orchestrator import _try_llm_narrative

    class _FailingProvider:
        def generate_narrative(self, context):
            raise LLMUnavailable("simulated failure")

    monkeypatch.setattr("app.agents.orchestrator.get_llm_provider", lambda: _FailingProvider())

    result = _try_llm_narrative(
        {"predicted_industry": "healthcare", "confidence": 0.9, "is_uncertain": False},
        {"overall_score": 45, "level": "developing"},
        {"strengths": [], "weaknesses": [], "missing_evidence": []},
        {"startup_name": "Nova", "startup_description": "desc"},
    )
    assert result is None
