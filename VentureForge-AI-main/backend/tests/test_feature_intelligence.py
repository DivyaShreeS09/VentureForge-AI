from app.agents.feature_intelligence import _FEATURE_IDEAS, build_feature_intelligence

_REQUIRED_KEYS = {
    "ai_feature", "automation", "analytics", "integrations",
    "premium_tier", "enterprise_feature", "future_roadmap", "monetization_opportunity",
}


def test_every_required_category_is_populated_with_idea_and_why():
    result = build_feature_intelligence("Restaurant Operations Technology", "b2b", ["Restaurants"], True)
    assert _REQUIRED_KEYS.issubset(result.keys())
    for key in _REQUIRED_KEYS:
        assert result[key]["idea"], f"{key} idea must not be empty"
        assert result[key]["why"], f"{key} why must not be empty"


def test_never_just_says_needs_differentiation():
    result = build_feature_intelligence(None, "b2b", [], True)
    for key in _REQUIRED_KEYS:
        text = result[key]["idea"].lower()
        assert "needs differentiation" not in text
        assert len(text) > 20  # a substantive idea, not a one-word placeholder


def test_different_categories_produce_different_ideas():
    healthcare = build_feature_intelligence(None, "healthcare", [], True)
    developer_tools = build_feature_intelligence("Developer platform", None, [], True)
    assert healthcare["ai_feature"] != developer_tools["ai_feature"]
    assert healthcare["enterprise_feature"] != developer_tools["enterprise_feature"]


def test_unknown_category_falls_back_to_generic():
    result = build_feature_intelligence("Some Totally Novel Category", None, [], True)
    assert result["ai_feature"] == _FEATURE_IDEAS["generic"]["ai_feature"]


def test_differentiation_weak_flag_changes_framing_not_presence_of_ideas():
    weak = build_feature_intelligence(None, "b2b", [], True)
    strong = build_feature_intelligence(None, "b2b", [], False)
    assert weak["differentiation_is_weak"] is True
    assert strong["differentiation_is_weak"] is False
    # Ideas themselves are still fully produced either way — never withheld.
    for key in _REQUIRED_KEYS:
        assert weak[key] == strong[key]
    assert weak["framing_note"] != strong["framing_note"]


def test_never_claims_this_ventures_actual_capabilities():
    result = build_feature_intelligence(None, "b2b", [], True)
    assert "deterministic" in result["source"].lower()
    assert "never a claim" in result["source"].lower()


def test_next_build_recommendation_uses_real_capability_signal_not_category():
    recommended_cap = {"label": "Automated Waste Tracking", "reason": "Not present yet", "description": "desc", "validation_question": "Does waste tracking work for one site yet?"}
    result = build_feature_intelligence(
        None, "b2b", [], True,
        venture_signals={"top_recommended_capability": recommended_cap, "top_present_capability": None},
    )
    assert result["next_build_recommendation"]["idea"] == "Automated Waste Tracking"
    assert result["next_build_recommendation"]["how_to_validate"] == "Does waste tracking work for one site yet?"


def test_next_build_recommendation_absent_signal_never_fabricates():
    result = build_feature_intelligence(None, "b2b", [], True)
    assert result["next_build_recommendation"]["idea"] is None
    assert "not enough evidence" in result["next_build_recommendation"]["why"].lower()


def test_startup_description_recovers_cybersecurity_from_coarse_b2b_fallback():
    generic_b2b = build_feature_intelligence("b2b", "b2b", [], True)
    cybersecurity = build_feature_intelligence(
        "b2b", "b2b", [], True,
        startup_description="Automated penetration testing for mid-size SaaS companies.",
    )
    assert cybersecurity["ai_feature"] != generic_b2b["ai_feature"]
