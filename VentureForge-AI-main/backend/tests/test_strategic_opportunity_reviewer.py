"""Gemini Strategic Opportunity reviewer safety tests (Phase 3). CI never requires a live Gemini
key — every provider call here is mocked at the httpx layer, exactly like
test_idea_expansion_reviewer.py.
"""

import json

import httpx
import pytest

from app.agents.strategic_opportunity import build_deterministic_strategic_opportunity
from app.agents.strategic_opportunity_reviewer import (
    build_strategic_opportunity_context,
    generate_strategic_opportunity_safely,
    merge_gemini_strategic_opportunity_into_baseline,
)
from app.ai import factory
from app.ai.base import LLMUnavailable
from app.ai.gemini_provider import GeminiProvider
from app.ai.schemas import GeminiStrategicOpportunity

_VENTURE_POSITIONING = {
    "primary_domain": "Smart Facilities Technology",
    "secondary_domains": ["PropTech"],
    "deployment_sectors": ["Campuses", "Hotels"],
}
_FEATURE_GAP = {
    "present_capabilities": [{"id": "real_time_utility_monitoring", "label": "Real-Time Utility Monitoring"}],
    "recommended_capabilities": [],
    "premature_capabilities": [],
    "not_relevant_capabilities": [],
}
_FOUNDER_GUIDANCE_ITEMS: list = []
_FUNDING_ASSESSMENT = {"level": "developing"}
_DESCRIPTION = "Software that monitors utility usage in real time across campus buildings."


def _baseline() -> dict:
    return build_deterministic_strategic_opportunity(
        _VENTURE_POSITIONING, None, None, None, None, _FEATURE_GAP, _FOUNDER_GUIDANCE_ITEMS, _FUNDING_ASSESSMENT
    )


def _valid_gemini_payload(**overrides) -> dict:
    payload = {
        "adjacent_opportunities": [
            {"opportunity": "Airports", "reason": "Airports run always-on facilities needing the same utility monitoring.", "evidence": "No direct evidence yet.", "confidence_tier": "reasonable_hypothesis", "recommended_next_step": "Interview an airport facilities lead."}
        ],
        "future_expansion": [
            {"opportunity": "Analytics Platform", "reason": "Utility data collected could feed a standalone analytics product.", "evidence": "Builds on existing monitoring capability.", "confidence_tier": "speculative_future_opportunity", "recommended_next_step": "Revisit after multiple pilots."}
        ],
        "strategic_risks": [
            {"risk": "Facilities budget cycles are slow", "category": "timing", "why": "Facilities budgets are often set a year in advance.", "likelihood": "medium", "impact": "medium", "mitigation": "Time outreach to the annual budget cycle.", "confidence_tier": "reasonable_hypothesis"}
        ],
    }
    payload.update(overrides)
    return payload


def _gemini_envelope(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _fake_response(json_body: dict) -> httpx.Response:
    request = httpx.Request("POST", "https://example.invalid")
    return httpx.Response(200, json=json_body, request=request)


def _context():
    return build_strategic_opportunity_context(
        "FacilitiesIQ", _DESCRIPTION, _VENTURE_POSITIONING, None, None, None, _FEATURE_GAP, "developing"
    )


@pytest.fixture(autouse=True)
def _clear_provider_cache():
    factory.get_llm_provider.cache_clear()
    yield
    factory.get_llm_provider.cache_clear()


# --- Schema-level guarantees ----------------------------------------------------------------------


def test_gemini_schema_cannot_express_confirmed_from_evidence():
    with pytest.raises(Exception):
        GeminiStrategicOpportunity.model_validate(
            _valid_gemini_payload(adjacent_opportunities=[{"opportunity": "x", "reason": "y", "evidence": "z", "confidence_tier": "confirmed_from_evidence", "recommended_next_step": "n"}])
        )


def test_gemini_schema_has_no_primary_opportunity_field():
    gemini = GeminiStrategicOpportunity.model_validate(_valid_gemini_payload())
    assert not hasattr(gemini, "primary_opportunity")


def test_gemini_schema_bounds_item_count():
    many = [{"opportunity": f"o{i}", "reason": "r", "evidence": "e", "confidence_tier": "reasonable_hypothesis", "recommended_next_step": "n"} for i in range(10)]
    gemini = GeminiStrategicOpportunity.model_validate(_valid_gemini_payload(adjacent_opportunities=many))
    assert len(gemini.adjacent_opportunities) == 4


# --- Merge-level safety checks ----------------------------------------------------------------------


def test_valid_response_is_appended_never_replacing_primary_opportunity():
    baseline = _baseline()
    gemini = GeminiStrategicOpportunity.model_validate(_valid_gemini_payload())
    merged = merge_gemini_strategic_opportunity_into_baseline(gemini, baseline)

    assert merged["source"] == "gemini_enhanced"
    assert merged["primary_opportunity"] == baseline["primary_opportunity"]
    assert any(i["opportunity"] == "Airports" and i["source"] == "gemini" for i in merged["adjacent_opportunities"])
    assert any(r["risk"] == "Facilities budget cycles are slow" and r["source"] == "gemini" for r in merged["strategic_risks"])


def test_named_company_is_rejected():
    baseline = _baseline()
    gemini = GeminiStrategicOpportunity.model_validate(
        _valid_gemini_payload(adjacent_opportunities=[{"opportunity": "Copy Acme Facilities Inc's model", "reason": "It works well.", "evidence": "e", "confidence_tier": "reasonable_hypothesis", "recommended_next_step": "n"}])
    )
    merged = merge_gemini_strategic_opportunity_into_baseline(gemini, baseline)
    assert not any(i["source"] == "gemini" for i in merged["adjacent_opportunities"])


def test_url_in_risk_is_rejected():
    baseline = _baseline()
    gemini = GeminiStrategicOpportunity.model_validate(
        _valid_gemini_payload(strategic_risks=[{"risk": "See https://example.com for details", "category": "market", "why": "w", "likelihood": "low", "impact": "low", "mitigation": "m", "confidence_tier": "reasonable_hypothesis"}])
    )
    merged = merge_gemini_strategic_opportunity_into_baseline(gemini, baseline)
    assert not any(r["source"] == "gemini" for r in merged["strategic_risks"])


def test_empty_gemini_response_keeps_source_deterministic():
    baseline = _baseline()
    gemini = GeminiStrategicOpportunity.model_validate({"adjacent_opportunities": [], "future_expansion": [], "strategic_risks": []})
    merged = merge_gemini_strategic_opportunity_into_baseline(gemini, baseline)
    assert merged["source"] == "deterministic"


def test_merge_never_mutates_the_original_baseline():
    baseline = _baseline()
    original_adjacent = list(baseline["adjacent_opportunities"])
    gemini = GeminiStrategicOpportunity.model_validate(_valid_gemini_payload())
    merge_gemini_strategic_opportunity_into_baseline(gemini, baseline)
    assert baseline["adjacent_opportunities"] == original_adjacent


# --- generate_strategic_opportunity_safely: end-to-end fallback behavior ---------------------------


def test_no_api_key_falls_back_to_deterministic_baseline(monkeypatch):
    monkeypatch.setattr("app.ai.factory.settings.gemini_api_key", None)
    baseline = _baseline()
    result = generate_strategic_opportunity_safely(_context(), baseline)
    assert result == baseline


def test_provider_unavailable_falls_back_to_deterministic_baseline(monkeypatch):
    class _FailingProvider:
        def generate_strategic_opportunity(self, context):
            raise LLMUnavailable("simulated failure")

    monkeypatch.setattr("app.agents.strategic_opportunity_reviewer.get_llm_provider", lambda: _FailingProvider())
    baseline = _baseline()
    result = generate_strategic_opportunity_safely(_context(), baseline)
    assert result == baseline


def test_unexpected_exception_falls_back_to_deterministic_baseline(monkeypatch):
    class _CrashingProvider:
        def generate_strategic_opportunity(self, context):
            raise RuntimeError("boom")

    monkeypatch.setattr("app.agents.strategic_opportunity_reviewer.get_llm_provider", lambda: _CrashingProvider())
    baseline = _baseline()
    result = generate_strategic_opportunity_safely(_context(), baseline)
    assert result == baseline


def test_malformed_json_falls_back_to_deterministic_baseline(monkeypatch):
    response = _fake_response(_gemini_envelope("not valid json{{"))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)
    provider = GeminiProvider(api_key="test-key")

    monkeypatch.setattr("app.agents.strategic_opportunity_reviewer.get_llm_provider", lambda: provider)
    baseline = _baseline()
    result = generate_strategic_opportunity_safely(_context(), baseline)
    assert result == baseline


def test_valid_provider_response_end_to_end_merges_successfully(monkeypatch):
    response = _fake_response(_gemini_envelope(json.dumps(_valid_gemini_payload())))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)
    provider = GeminiProvider(api_key="test-key")

    monkeypatch.setattr("app.agents.strategic_opportunity_reviewer.get_llm_provider", lambda: provider)
    baseline = _baseline()
    result = generate_strategic_opportunity_safely(_context(), baseline)
    assert result["source"] == "gemini_enhanced"
    assert result["primary_opportunity"] == baseline["primary_opportunity"]
