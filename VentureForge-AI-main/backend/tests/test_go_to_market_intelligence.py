from app.agents.go_to_market_intelligence import _GTM_VOCAB, build_go_to_market_intelligence

_REQUIRED_KEYS = {
    "who_to_approach_first",
    "first_twenty_customers_source",
    "early_adopter_profile",
    "outreach_strategy",
    "distribution_channels",
    "sales_motion",
    "validation_roadmap",
    "expansion_roadmap",
}


def test_every_required_founder_question_is_answered():
    result = build_go_to_market_intelligence("Restaurant Operations Technology", "b2b", ["Restaurants"], "developing")
    assert _REQUIRED_KEYS.issubset(result.keys())
    for key in _REQUIRED_KEYS:
        assert result[key], f"{key} must not be empty"


def test_different_categories_produce_genuinely_different_guidance():
    """The core anti-genericness guarantee: two different domains must not get byte-identical
    who_to_approach_first / early_adopter_profile text."""
    healthcare = build_go_to_market_intelligence(None, "healthcare", [], "early_stage")
    fintech = build_go_to_market_intelligence(None, "fintech", [], "early_stage")
    developer_tools = build_go_to_market_intelligence("Developer platform", None, [], "early_stage")
    assert healthcare["who_to_approach_first"] != fintech["who_to_approach_first"]
    assert healthcare["early_adopter_profile"] != developer_tools["early_adopter_profile"]
    assert fintech["sales_motion"] != developer_tools["sales_motion"]


def test_unknown_category_falls_back_to_generic_not_a_crash():
    result = build_go_to_market_intelligence("Some Totally Novel Category Nobody Has Seen", None, [], "early_stage")
    assert result["who_to_approach_first"] == _GTM_VOCAB["generic"]["who_to_approach_first"]


def test_pre_traction_validation_roadmap_differs_from_post_traction():
    early = build_go_to_market_intelligence(None, "b2b", [], "early_stage")
    ready = build_go_to_market_intelligence(None, "b2b", [], "ready")
    assert early["validation_roadmap"] != ready["validation_roadmap"]
    assert any("pilot" in step.lower() for step in early["validation_roadmap"])


def test_never_claims_specific_traction_about_this_venture():
    result = build_go_to_market_intelligence(None, "b2b", [], "early_stage")
    assert "customer" in result["source"].lower() or "traction" in result["source"].lower()
    assert "deterministic" in result["source"].lower()


def test_startup_description_recovers_specific_category_from_coarse_b2b_fallback():
    """Regression guard: when venture_positioning/model_category both collapse to the coarse 'b2b'
    label (very common per the Product Intelligence Sprint audit — a cybersecurity pentesting
    startup, a canteen SaaS, and a logistics routing tool all resolved to 'b2b' with no way to tell
    them apart), the raw startup_description must recover real category-specific guidance instead
    of byte-identical b2b boilerplate."""
    generic_b2b = build_go_to_market_intelligence("b2b", "b2b", [], "early_stage")
    cybersecurity = build_go_to_market_intelligence(
        "b2b", "b2b", [], "early_stage",
        startup_description="Automated penetration testing for mid-size SaaS companies.",
    )
    logistics = build_go_to_market_intelligence(
        "b2b", "b2b", [], "early_stage",
        startup_description="Optimizing last-mile delivery routes for e-commerce companies.",
    )
    assert cybersecurity["who_to_approach_first"] != generic_b2b["who_to_approach_first"]
    assert logistics["who_to_approach_first"] != generic_b2b["who_to_approach_first"]
    assert cybersecurity["who_to_approach_first"] != logistics["who_to_approach_first"]


def test_prototype_signal_replaces_generic_discovery_step_with_concrete_deployment_test():
    no_signal = build_go_to_market_intelligence(None, "b2b", [], "early_stage")
    with_prototype = build_go_to_market_intelligence(
        None, "b2b", [], "early_stage",
        venture_signals={"has_prototype": True, "deployment_sectors": ["college cafeterias"]},
    )
    assert "college cafeterias" in with_prototype["validation_roadmap"][0]
    assert with_prototype["validation_roadmap"][0] != no_signal["validation_roadmap"][0]


def test_no_venture_signals_produces_no_personalization_fabrication():
    result = build_go_to_market_intelligence(None, "b2b", [], "early_stage")
    assert result["personalization"] == []
