from app.agents.competitor_intelligence import _COMPETITOR_PATTERNS, build_competitor_intelligence

_REQUIRED_KEYS = {"likely_customer_alternatives", "switching_behavior", "switching_friction", "how_to_win"}


def test_every_required_field_is_populated():
    result = build_competitor_intelligence("Restaurant Operations Technology", "b2b", ["Restaurants"], True)
    assert _REQUIRED_KEYS.issubset(result.keys())
    assert len(result["likely_customer_alternatives"]) >= 2
    assert result["switching_behavior"]
    assert result["switching_friction"]
    assert result["how_to_win"]


def test_different_categories_produce_different_analysis():
    healthcare = build_competitor_intelligence(None, "healthcare", [], False)
    developer_tools = build_competitor_intelligence("Developer platform", None, [], False)
    assert healthcare["how_to_win"] != developer_tools["how_to_win"]
    assert healthcare["switching_friction"] != developer_tools["switching_friction"]


def test_unknown_category_falls_back_to_generic():
    result = build_competitor_intelligence("Some Totally Novel Category", None, [], False)
    assert result["how_to_win"] == _COMPETITOR_PATTERNS["generic"]["how_to_win"]


def test_framing_note_differs_with_named_competitors_present():
    with_named = build_competitor_intelligence(None, "b2b", [], True)
    without_named = build_competitor_intelligence(None, "b2b", [], False)
    assert with_named["framing_note"] != without_named["framing_note"]
    assert "supplements" in with_named["framing_note"].lower()
    assert "naming 2-3 real" in without_named["framing_note"].lower()


def test_never_claims_a_specific_real_company():
    result = build_competitor_intelligence(None, "b2b", [], False)
    assert "never a claim about a specific real company" in result["source"].lower()
    # Category-level phrasing only — every pattern across every category uses generic language,
    # never a specific real product/brand name.
    all_text = " ".join(
        alt for pattern in _COMPETITOR_PATTERNS.values() for alt in pattern["customer_alternatives"]
    )
    for banned_brand in ("toast", "salesforce", "epic", "google", "microsoft", "stripe"):
        assert banned_brand not in all_text.lower()


def test_named_competitor_context_uses_founders_own_list():
    result = build_competitor_intelligence(
        None, "b2b", [], True, venture_signals={"known_competitors": ["Toast POS", "Zomato"]}
    )
    assert "Toast POS" in result["named_competitor_context"]


def test_no_known_competitors_never_fabricates_a_name():
    result = build_competitor_intelligence(None, "b2b", [], False)
    assert "Toast" not in result["named_competitor_context"]
    assert "naming 2-3 real" in result["named_competitor_context"].lower()


def test_startup_description_recovers_logistics_from_coarse_b2b_fallback():
    generic_b2b = build_competitor_intelligence("b2b", "b2b", [], False)
    logistics = build_competitor_intelligence(
        "b2b", "b2b", [], False,
        startup_description="Optimizing last-mile delivery routes for e-commerce companies.",
    )
    assert logistics["how_to_win"] != generic_b2b["how_to_win"]
