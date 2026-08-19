"""Deterministic Idea Expansion baseline tests (Phase 2). No network — see
test_idea_expansion_reviewer.py for the Gemini-additive layer.
"""

from app.agents.idea_expansion import build_deterministic_idea_expansion

_VENTURE_POSITIONING = {
    "primary_domain": "Restaurant Operations Technology",
    "secondary_domains": ["Food-Cost Management"],
    "deployment_sectors": ["Restaurants"],
    "confidence": 0.8,
    "is_low_confidence": False,
}
_FEATURE_GAP = {
    "present_capabilities": [{"id": "manual_inventory_logging", "label": "Manual Inventory Logging"}],
    "recommended_capabilities": [
        {"id": "pos_integration", "label": "POS Integration", "reason": "A strong next capability to build."}
    ],
    "premature_capabilities": [
        {
            "id": "automated_reorder_suggestions",
            "label": "Automated Reorder Suggestions",
            "reason": "A great next step once pos_integration is in place.",
        }
    ],
    "not_relevant_capabilities": [],
}
_MVP_RECOMMENDATION = {
    "minimum_workflow": "Manual Inventory Logging, applied to one pilot only.",
    "pilot_environment": "One real restaurant, not a broad launch.",
    "single_core_problem": "The narrowest version of the food-waste problem.",
}


def _build():
    return build_deterministic_idea_expansion(_VENTURE_POSITIONING, _FEATURE_GAP, _MVP_RECOMMENDATION)


def test_returns_all_eight_categories():
    result = _build()
    for key in (
        "customer_segments", "adjacent_industries", "feature_ideas", "pricing_models",
        "mvp_simplification", "pivot_opportunities", "partnerships", "go_to_market",
    ):
        assert key in result


def test_deterministic_source_and_version():
    result = _build()
    assert result["source"] == "deterministic"
    assert result["idea_expansion_version"] == "v1"


def test_customer_segments_derived_from_deployment_sectors_are_confirmed_from_evidence():
    result = _build()
    assert len(result["customer_segments"]) == 1
    item = result["customer_segments"][0]
    assert item["title"] == "Restaurants"
    assert item["confidence_tier"] == "confirmed_from_evidence"


def test_adjacent_industries_derived_from_secondary_domains_are_confirmed_from_evidence():
    result = _build()
    assert len(result["adjacent_industries"]) == 1
    assert result["adjacent_industries"][0]["title"] == "Food-Cost Management"
    assert result["adjacent_industries"][0]["confidence_tier"] == "confirmed_from_evidence"


def test_feature_ideas_split_recommended_vs_premature_tiers():
    result = _build()
    titles_to_tiers = {i["title"]: i["confidence_tier"] for i in result["feature_ideas"]}
    assert titles_to_tiers["Build: POS Integration"] == "reasonable_hypothesis"
    assert titles_to_tiers["Later: Automated Reorder Suggestions"] == "speculative_future_opportunity"


def test_pricing_models_are_generic_and_never_confirmed_from_evidence():
    result = _build()
    assert len(result["pricing_models"]) >= 4
    assert all(i["confidence_tier"] == "reasonable_hypothesis" for i in result["pricing_models"])


def test_pivot_opportunities_never_say_you_should_pivot():
    result = _build()
    assert result["pivot_opportunities"]
    for item in result["pivot_opportunities"]:
        assert "you should pivot" not in item["reason"].lower()
        assert "if adoption in" in item["reason"].lower()


def test_mvp_simplification_has_staged_structure():
    result = _build()
    mvp = result["mvp_simplification"]
    assert mvp["simplest_mvp"] == _MVP_RECOMMENDATION["minimum_workflow"]
    assert "POS Integration" in mvp["version_2"]
    assert "Automated Reorder Suggestions" in mvp["version_3"]
    assert mvp["confidence_tier"] == "confirmed_from_evidence"


def test_partnerships_include_sector_specific_and_generic_categories():
    result = _build()
    titles = [i["title"] for i in result["partnerships"]]
    assert any("point-of-sale" in t.lower() or "pos" in t.lower() for t in titles)
    assert any("cloud" in t.lower() for t in titles)


def test_go_to_market_references_pilot_plan():
    result = _build()
    assert result["go_to_market"]
    assert all(i["confidence_tier"] == "reasonable_hypothesis" for i in result["go_to_market"])


def test_no_primary_domain_degrades_gracefully_without_crashing():
    result = build_deterministic_idea_expansion({}, _FEATURE_GAP, _MVP_RECOMMENDATION)
    assert result["adjacent_industries"] == []
    assert result["pivot_opportunities"] == []
    assert result["customer_segments"] == []
