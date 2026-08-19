"""Gemini Idea Expansion reviewer safety tests (Phase 2). CI never requires a live Gemini key —
every provider call here is mocked at the httpx layer, exactly like test_mentor_reviewer.py.
"""

import json

import httpx
import pytest

from app.agents.idea_expansion import build_deterministic_idea_expansion
from app.agents.idea_expansion_reviewer import (
    build_idea_expansion_context,
    generate_idea_expansion_safely,
    merge_gemini_idea_expansion_into_baseline,
)
from app.ai import factory
from app.ai.base import LLMUnavailable
from app.ai.gemini_provider import GeminiProvider
from app.ai.schemas import GeminiIdeaExpansion

_VENTURE_POSITIONING = {
    "primary_domain": "Restaurant Operations Technology",
    "secondary_domains": ["Food-Cost Management"],
    "deployment_sectors": ["Restaurants"],
}
_FEATURE_GAP = {
    "present_capabilities": [{"id": "manual_inventory_logging", "label": "Manual Inventory Logging"}],
    "recommended_capabilities": [
        {"id": "pos_integration", "label": "POS Integration", "reason": "A strong next capability to build."}
    ],
    "premature_capabilities": [],
    "not_relevant_capabilities": [],
}
_MVP_RECOMMENDATION = {
    "minimum_workflow": "Manual Inventory Logging, applied to one pilot only.",
    "pilot_environment": "One real restaurant, not a broad launch.",
    "single_core_problem": "The narrowest version of the food-waste problem.",
}
_DESCRIPTION = "Software that helps small restaurants track inventory and reduce food waste."


def _baseline() -> dict:
    return build_deterministic_idea_expansion(_VENTURE_POSITIONING, _FEATURE_GAP, _MVP_RECOMMENDATION)


def _valid_gemini_payload(**overrides) -> dict:
    payload = {
        "customer_segments": [
            {"title": "Meal-kit kitchens", "reason": "Similar batch-inventory needs.", "confidence_tier": "reasonable_hypothesis"}
        ],
        "adjacent_industries": [],
        "feature_ideas": [
            {"title": "Offline mode", "reason": "Kitchens often have unreliable wifi.", "confidence_tier": "reasonable_hypothesis"}
        ],
        "pricing_models": [],
        "pivot_opportunities": [],
        "partnerships": [
            {"title": "Microsoft for Startups", "reason": "Could be a relevant partner for cloud credits.", "confidence_tier": "speculative_future_opportunity"}
        ],
        "go_to_market": [],
    }
    payload.update(overrides)
    return payload


def _gemini_envelope(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _fake_response(json_body: dict) -> httpx.Response:
    request = httpx.Request("POST", "https://example.invalid")
    return httpx.Response(200, json=json_body, request=request)


def _context():
    return build_idea_expansion_context(
        "WasteLess", _DESCRIPTION, _VENTURE_POSITIONING, _FEATURE_GAP, _MVP_RECOMMENDATION, "developing"
    )


@pytest.fixture(autouse=True)
def _clear_provider_cache():
    factory.get_llm_provider.cache_clear()
    yield
    factory.get_llm_provider.cache_clear()


# --- Schema-level guarantees ----------------------------------------------------------------------


def test_gemini_schema_cannot_express_confirmed_from_evidence():
    with pytest.raises(Exception):
        GeminiIdeaExpansion.model_validate(
            _valid_gemini_payload(customer_segments=[{"title": "x", "reason": "y", "confidence_tier": "confirmed_from_evidence"}])
        )


def test_gemini_schema_bounds_item_count_per_category():
    many_items = [{"title": f"idea {i}", "reason": "r", "confidence_tier": "reasonable_hypothesis"} for i in range(10)]
    gemini = GeminiIdeaExpansion.model_validate(_valid_gemini_payload(feature_ideas=many_items))
    assert len(gemini.feature_ideas) == 4


# --- Merge-level safety checks (unit, no network) --------------------------------------------------


def test_valid_response_is_appended_never_replacing_deterministic_items():
    baseline = _baseline()
    original_pricing_count = len(baseline["pricing_models"])
    gemini = GeminiIdeaExpansion.model_validate(_valid_gemini_payload())
    merged = merge_gemini_idea_expansion_into_baseline(gemini, baseline)

    assert merged["source"] == "gemini_enhanced"
    # Deterministic items are still all present, unchanged.
    assert len(merged["pricing_models"]) == original_pricing_count
    assert merged["mvp_simplification"] == baseline["mvp_simplification"]
    # New Gemini item was appended.
    assert any(i["title"] == "Offline mode" and i["source"] == "gemini" for i in merged["feature_ideas"])
    assert all(i["confidence_tier"] != "confirmed_from_evidence" for i in merged["feature_ideas"] if i["source"] == "gemini")


def test_named_company_in_non_partnership_category_is_rejected():
    baseline = _baseline()
    gemini = GeminiIdeaExpansion.model_validate(
        _valid_gemini_payload(feature_ideas=[{"title": "Copy Toast POS Inc's reorder flow", "reason": "It works well.", "confidence_tier": "reasonable_hypothesis"}])
    )
    merged = merge_gemini_idea_expansion_into_baseline(gemini, baseline)
    assert not any(i["source"] == "gemini" for i in merged["feature_ideas"])


def test_named_company_in_partnerships_is_allowed():
    baseline = _baseline()
    gemini = GeminiIdeaExpansion.model_validate(_valid_gemini_payload())
    merged = merge_gemini_idea_expansion_into_baseline(gemini, baseline)
    assert any(i["title"] == "Microsoft for Startups" and i["source"] == "gemini" for i in merged["partnerships"])


def test_url_in_partnerships_is_still_rejected():
    baseline = _baseline()
    gemini = GeminiIdeaExpansion.model_validate(
        _valid_gemini_payload(partnerships=[{"title": "Partner at https://example.com/signup", "reason": "See link.", "confidence_tier": "reasonable_hypothesis"}])
    )
    merged = merge_gemini_idea_expansion_into_baseline(gemini, baseline)
    assert not any(i["source"] == "gemini" for i in merged["partnerships"])


def test_empty_gemini_response_keeps_source_deterministic():
    baseline = _baseline()
    gemini = GeminiIdeaExpansion.model_validate(
        {k: [] for k in ("customer_segments", "adjacent_industries", "feature_ideas", "pricing_models", "pivot_opportunities", "partnerships", "go_to_market")}
    )
    merged = merge_gemini_idea_expansion_into_baseline(gemini, baseline)
    assert merged["source"] == "deterministic"


def test_merge_never_mutates_the_original_baseline():
    baseline = _baseline()
    original_feature_ideas = list(baseline["feature_ideas"])
    gemini = GeminiIdeaExpansion.model_validate(_valid_gemini_payload())
    merge_gemini_idea_expansion_into_baseline(gemini, baseline)
    assert baseline["feature_ideas"] == original_feature_ideas


# --- generate_idea_expansion_safely: end-to-end fallback behavior ----------------------------------


def test_no_api_key_falls_back_to_deterministic_baseline(monkeypatch):
    monkeypatch.setattr("app.ai.factory.settings.gemini_api_key", None)
    baseline = _baseline()
    result = generate_idea_expansion_safely(_context(), baseline)
    assert result == baseline


def test_provider_unavailable_falls_back_to_deterministic_baseline(monkeypatch):
    class _FailingProvider:
        def generate_idea_expansion(self, context):
            raise LLMUnavailable("simulated failure")

    monkeypatch.setattr("app.agents.idea_expansion_reviewer.get_llm_provider", lambda: _FailingProvider())
    baseline = _baseline()
    result = generate_idea_expansion_safely(_context(), baseline)
    assert result == baseline


def test_unexpected_exception_falls_back_to_deterministic_baseline(monkeypatch):
    class _CrashingProvider:
        def generate_idea_expansion(self, context):
            raise RuntimeError("boom")

    monkeypatch.setattr("app.agents.idea_expansion_reviewer.get_llm_provider", lambda: _CrashingProvider())
    baseline = _baseline()
    result = generate_idea_expansion_safely(_context(), baseline)
    assert result == baseline


def test_malformed_json_falls_back_to_deterministic_baseline(monkeypatch):
    response = _fake_response(_gemini_envelope("not valid json{{"))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)
    provider = GeminiProvider(api_key="test-key")

    monkeypatch.setattr("app.agents.idea_expansion_reviewer.get_llm_provider", lambda: provider)
    baseline = _baseline()
    result = generate_idea_expansion_safely(_context(), baseline)
    assert result == baseline


def test_valid_provider_response_end_to_end_merges_successfully(monkeypatch):
    response = _fake_response(_gemini_envelope(json.dumps(_valid_gemini_payload())))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)
    provider = GeminiProvider(api_key="test-key")

    monkeypatch.setattr("app.agents.idea_expansion_reviewer.get_llm_provider", lambda: provider)
    baseline = _baseline()
    result = generate_idea_expansion_safely(_context(), baseline)
    assert result["source"] == "gemini_enhanced"
    assert result["mvp_simplification"] == baseline["mvp_simplification"]
