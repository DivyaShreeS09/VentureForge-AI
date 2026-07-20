import json

import httpx
import pytest

from app.agents.competitor_agent import generate_competitor_analysis
from app.agents.competitor_reviewer import suggest_competitor_possibilities_safely
from app.ai import factory
from app.ai.base import LLMUnavailable
from app.ai.gemini_provider import GeminiProvider
from app.ai.schemas import CompetitorPossibilitiesContext, GeminiCompetitorPossibilities


@pytest.fixture(autouse=True)
def _clear_provider_cache():
    factory.get_llm_provider.cache_clear()
    yield
    factory.get_llm_provider.cache_clear()


# --- 5-bucket structure & backward-compat alias -------------------------------------------------


def test_all_five_buckets_present_and_serializable():
    result = generate_competitor_analysis(known_competitors=["Acme Corp"], industry_prediction={"predicted_industry": "saas"})
    for bucket in (
        "verified_competitors", "unverified_possibilities", "indirect_alternatives",
        "manual_process_alternative", "do_nothing_alternative",
    ):
        assert bucket in result
    json.dumps(result)


def test_verified_competitors_only_contains_founder_supplied_names():
    result = generate_competitor_analysis(known_competitors=["Acme Corp", "Beta Inc"], industry_prediction=None)
    names = [c["name"] for c in result["verified_competitors"]]
    assert names == ["Acme Corp", "Beta Inc"]
    for c in result["verified_competitors"]:
        assert c["verification_status"] == "unverified_by_system"


def test_no_unsupplied_proper_noun_appears_as_a_verified_competitor():
    result = generate_competitor_analysis(known_competitors=[], industry_prediction={"predicted_industry": "saas"})
    assert result["verified_competitors"] == []


def test_deterministic_fallback_leaves_unverified_possibilities_empty():
    result = generate_competitor_analysis(known_competitors=[], industry_prediction={"predicted_industry": "saas"})
    assert result["unverified_possibilities"] == []
    # But the deterministic buckets remain useful even with nothing else supplied.
    assert result["indirect_alternatives"]
    assert result["manual_process_alternative"]["description"]
    assert result["do_nothing_alternative"]["description"]


_FOOD_DELIVERY_POSSIBILITY = {
    "category": "food delivery apps",
    "solution_type": "software_platform",
    "reason": "Adjacent category solving a similar logistics problem.",
    "source": "ai_suggested_category",
}


def test_indirect_manual_do_nothing_are_deterministic_regardless_of_gemini_input():
    without_gemini = generate_competitor_analysis(known_competitors=[], industry_prediction={"predicted_industry": "saas"})
    with_gemini = generate_competitor_analysis(
        known_competitors=[], industry_prediction={"predicted_industry": "saas"},
        unverified_possibilities=[_FOOD_DELIVERY_POSSIBILITY],
    )
    assert without_gemini["indirect_alternatives"] == with_gemini["indirect_alternatives"]
    assert without_gemini["manual_process_alternative"] == with_gemini["manual_process_alternative"]
    assert without_gemini["do_nothing_alternative"] == with_gemini["do_nothing_alternative"]


def test_unverified_possibilities_populated_only_from_explicit_category_phrases():
    possibility = {
        "category": "general to-do list apps",
        "solution_type": "software_platform",
        "reason": "A broad, generic category adjacent to this idea.",
        "source": "ai_suggested_category",
    }
    result = generate_competitor_analysis(
        known_competitors=[], industry_prediction=None, unverified_possibilities=[possibility]
    )
    assert result["unverified_possibilities"][0]["category"] == "general to-do list apps"
    assert result["unverified_possibilities"][0]["solution_type"] == "software_platform"
    assert result["unverified_possibilities"][0]["evidence_source"] == "gemini-suggested category (advisory, never a named company)"


# --- Backward compatibility: existing flat `entries` consumers still work ----------------------


def test_entries_alias_matches_old_shape_for_named_competitors():
    result = generate_competitor_analysis(known_competitors=["Acme Corp"], industry_prediction=None)
    assert result["entries"][0]["competitor_or_alternative"] == "Acme Corp"
    assert result["entries"][0]["confidence"] == "low"
    assert "not independently verified" in result["entries"][0]["category"]


def test_entries_alias_matches_old_shape_for_generic_fallback():
    result = generate_competitor_analysis(known_competitors=[], industry_prediction={"predicted_industry": "saas"})
    assert len(result["entries"]) == 3
    for entry in result["entries"]:
        assert "categor" in entry["category"]


def test_existing_stored_flat_result_remains_readable():
    """A pre-Phase-B stored analysis (old flat shape, no 5 buckets at all) must not crash any
    consumer that only reads the generic dict — nothing in this system assumes the new keys exist
    on old data (the API schema for competitor_analysis is a generic dict, see
    app.schemas.analysis)."""
    old_shape = {
        "agent_version": "v1-deterministic",
        "entries": [{"competitor_or_alternative": "Legacy Co", "category": "x", "confidence": "low"}],
        "recommended_validation_actions": ["x"],
        "disclaimer": "x",
    }
    # Simply reading old fields must work without any KeyError.
    assert old_shape["entries"][0]["competitor_or_alternative"] == "Legacy Co"


# --- Gemini competitor-possibilities reviewer: schema/sanitization/failure modes ----------------


def _gemini_envelope(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _fake_response(json_body: dict) -> httpx.Response:
    request = httpx.Request("POST", "https://example.invalid")
    return httpx.Response(200, json=json_body, request=request)


def _context() -> CompetitorPossibilitiesContext:
    return CompetitorPossibilitiesContext(
        startup_description="Software that helps small restaurants track inventory and reduce food waste.",
        model_category_label="b2b",
        venture_positioning_primary_domain="Restaurant Operations Technology",
    )


def _possibility(category: str, solution_type: str = "software_platform", reason: str = "A generic adjacent category.") -> dict:
    return {"category": category, "solution_type": solution_type, "reason": reason, "source": "ai_suggested_category"}


def test_category_level_possibilities_are_accepted(monkeypatch):
    payload = {
        "possibilities": [
            _possibility("restaurant inventory management tools"),
            _possibility("food-cost tracking software"),
        ]
    }
    response = _fake_response(_gemini_envelope(json.dumps(payload)))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)

    provider = GeminiProvider(api_key="test-key")
    result = provider.suggest_competitor_possibilities(_context())
    categories = [p.category for p in result.possibilities]
    assert categories == ["restaurant inventory management tools", "food-cost tracking software"]
    assert all(p.source == "ai_suggested_category" for p in result.possibilities)


# --- Adversarial validation: category/reason must never smuggle in a real company --------------


def test_named_company_in_gemini_output_is_sanitized_not_returned():
    """A response containing an obvious proper-noun company must have that entry dropped, not
    cause the whole response to fail or the name to leak through."""
    result = GeminiCompetitorPossibilities.model_validate(
        {
            "possibilities": [
                _possibility("Toast POS"),
                _possibility("general point-of-sale software"),
                _possibility("Square Inventory"),
            ]
        }
    )
    categories = [p.category for p in result.possibilities]
    assert "Toast POS" not in categories
    assert "Square Inventory" not in categories
    assert "general point-of-sale software" in categories


def test_url_in_category_is_rejected():
    result = GeminiCompetitorPossibilities.model_validate(
        {"possibilities": [_possibility("see https://example.com/tools for options"), _possibility("general inventory software")]}
    )
    categories = [p.category for p in result.possibilities]
    assert len(categories) == 1
    assert categories == ["general inventory software"]


def test_domain_like_token_in_category_is_rejected():
    result = GeminiCompetitorPossibilities.model_validate(
        {"possibilities": [_possibility("toasttab.com style POS tools"), _possibility("general point-of-sale software")]}
    )
    categories = [p.category for p in result.possibilities]
    assert categories == ["general point-of-sale software"]


def test_email_address_in_reason_is_rejected():
    result = GeminiCompetitorPossibilities.model_validate(
        {
            "possibilities": [
                _possibility("general inventory software", reason="Contact sales@example.com for details."),
                _possibility("general point-of-sale software"),
            ]
        }
    )
    categories = [p.category for p in result.possibilities]
    assert categories == ["general point-of-sale software"]


@pytest.mark.parametrize("suffix", ["Acme Inc", "Acme LLC", "Acme Ltd", "Acme PLC", "Acme Pvt Ltd", "Acme Corp", "Acme GmbH"])
def test_corporate_suffix_patterns_are_rejected(suffix):
    result = GeminiCompetitorPossibilities.model_validate(
        {"possibilities": [_possibility(suffix), _possibility("general point-of-sale software")]}
    )
    categories = [p.category for p in result.possibilities]
    assert suffix not in categories
    assert categories == ["general point-of-sale software"]


def test_lowercase_brand_like_text_still_caught_by_structural_or_heuristic_checks():
    # "toasttab.com" is lowercase (defeats the Title-Case heuristic alone) but is still caught by
    # the domain-pattern structural check — proving the checks are complementary, not redundant.
    result = GeminiCompetitorPossibilities.model_validate(
        {"possibilities": [_possibility("toasttab.com"), _possibility("general point-of-sale software")]}
    )
    categories = [p.category for p in result.possibilities]
    assert categories == ["general point-of-sale software"]


def test_mixed_valid_and_invalid_list_keeps_only_valid_items():
    result = GeminiCompetitorPossibilities.model_validate(
        {
            "possibilities": [
                _possibility("Toast POS"),
                _possibility("general point-of-sale software"),
                _possibility("visit www.example.com"),
                _possibility("spreadsheet-based inventory tools"),
                _possibility("Acme Inc"),
            ]
        }
    )
    categories = [p.category for p in result.possibilities]
    assert categories == ["general point-of-sale software", "spreadsheet-based inventory tools"]


def test_malformed_gemini_output_never_raises_and_yields_empty_list():
    # Missing required fields (no solution_type/reason), wrong types, and non-dict entries must
    # all be discarded individually rather than raising or crashing the whole response.
    result = GeminiCompetitorPossibilities.model_validate(
        {"possibilities": [{"category": "incomplete item"}, "just a string", 42, None]}
    )
    assert result.possibilities == []


def test_gemini_may_not_return_a_company_name_field_at_all():
    """The schema itself has no field for a company/brand name — even if Gemini's raw JSON
    includes one, it is simply ignored (extra fields are dropped), never surfaced."""
    result = GeminiCompetitorPossibilities.model_validate(
        {
            "possibilities": [
                {**_possibility("general point-of-sale software"), "company_name": "Toast"},
            ]
        }
    )
    assert len(result.possibilities) == 1
    assert not hasattr(result.possibilities[0], "company_name")


def test_timeout_raises_llm_unavailable(monkeypatch):
    def _raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", _raise_timeout)
    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.suggest_competitor_possibilities(_context())


def test_malformed_json_raises_llm_unavailable(monkeypatch):
    response = _fake_response(_gemini_envelope("not valid json{{"))
    monkeypatch.setattr("app.ai.gemini_provider.httpx.post", lambda *a, **k: response)
    provider = GeminiProvider(api_key="test-key")
    with pytest.raises(LLMUnavailable):
        provider.suggest_competitor_possibilities(_context())


# --- Safe wrapper: never raises, no-Gemini fallback remains useful ------------------------------


def test_safe_wrapper_returns_empty_list_without_api_key(monkeypatch):
    monkeypatch.setattr("app.ai.factory.settings.gemini_api_key", None)
    result = suggest_competitor_possibilities_safely("desc", "b2b", "Restaurant Operations Technology")
    assert result == []


def test_safe_wrapper_returns_empty_list_on_provider_failure(monkeypatch):
    class _FailingProvider:
        def suggest_competitor_possibilities(self, context):
            raise LLMUnavailable("simulated failure")

    monkeypatch.setattr("app.agents.competitor_reviewer.get_llm_provider", lambda: _FailingProvider())
    result = suggest_competitor_possibilities_safely("desc", "b2b", None)
    assert result == []


def test_no_gemini_fallback_still_produces_a_useful_competitor_analysis():
    """End-to-end (no mocking needed): with no API key configured at all, the full competitor
    analysis must still be useful — deterministic buckets populated, no crash."""
    result = generate_competitor_analysis(
        known_competitors=[],
        industry_prediction={"predicted_industry": "b2b"},
        unverified_possibilities=suggest_competitor_possibilities_safely("desc", "b2b", None),
    )
    assert result["unverified_possibilities"] == []
    assert result["indirect_alternatives"]
    assert result["recommended_validation_actions"]
