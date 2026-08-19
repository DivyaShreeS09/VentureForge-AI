from app.agents.pricing_intelligence import build_pricing_intelligence


def _vp(primary_domain="Restaurant Operations Technology", is_low_confidence=False):
    return {"primary_domain": primary_domain, "is_low_confidence": is_low_confidence}


def test_india_evidence_recommends_inr_with_confident_point_estimate():
    result = build_pricing_intelligence(
        _vp(), {"label": "b2b"}, {"target_market": "Restaurant owners in Bengaluru"}, "A tool for Indian restaurants."
    )
    assert result["currency"] == "INR"
    assert result["target_market"] == "india"
    assert result["target_market_is_assumption"] is False
    assert result["confidence"] == "high"
    assert result["recommended_price_per_customer"] is not None
    assert result["recommended_price_range"] is None
    assert result["recommended_price_per_customer"] > 0


def test_international_evidence_recommends_usd():
    result = build_pricing_intelligence(
        _vp(), {"label": "b2b"}, {"target_market": "Restaurant chains across the United States"}, "US restaurant software."
    )
    assert result["currency"] == "USD"
    assert result["target_market"] == "international"
    assert result["target_market_is_assumption"] is False
    assert result["recommended_price_per_customer"] is not None


def test_no_signal_defaults_to_india_flagged_as_assumption():
    result = build_pricing_intelligence(_vp(), {"label": "b2b"}, {}, "A tool for restaurant inventory.")
    assert result["currency"] == "INR"
    assert result["target_market"] == "india"
    assert result["target_market_is_assumption"] is True
    assert result["confidence"] == "low"
    assert result["recommended_price_per_customer"] is None
    assert result["recommended_price_range"] is not None
    assert result["recommended_price_range"]["low"] < result["recommended_price_range"]["high"]


def test_mixed_signal_is_genuinely_unclear():
    result = build_pricing_intelligence(
        _vp(), {"label": "b2b"}, {"target_market": "Starting in India, expanding to the United States"}, ""
    )
    assert result["target_market"] == "unclear"
    assert result["target_market_is_assumption"] is True
    assert result["recommended_price_range"] is not None


def test_generic_fallback_comparator_always_returns_a_range_even_with_confident_market():
    """No domain/category comparator at all (a truly novel category) means the price itself is
    weakly grounded, even if the target market is confidently known — must still be a range."""
    result = build_pricing_intelligence(
        {"primary_domain": "Some Never-Before-Seen Category"}, None,
        {"target_market": "Businesses across India"}, "",
    )
    assert result["target_market"] == "india"
    assert result["target_market_is_assumption"] is False
    assert result["confidence"] == "low"
    assert result["recommended_price_per_customer"] is None
    assert result["recommended_price_range"] is not None


def test_never_returns_both_point_estimate_and_range():
    for market_evidence in ({"target_market": "India"}, {}, {"target_market": "USA"}):
        result = build_pricing_intelligence(_vp(), {"label": "b2b"}, market_evidence, "")
        assert (result["recommended_price_per_customer"] is None) != (result["recommended_price_range"] is None)


def test_rationale_always_explains_why():
    result = build_pricing_intelligence(_vp(), {"label": "b2b"}, {"target_market": "India"}, "")
    assert len(result["rationale"]) >= 3
    assert all(isinstance(r, str) and r for r in result["rationale"])


def test_never_claims_live_market_data():
    result = build_pricing_intelligence(_vp(), {"label": "b2b"}, {"target_market": "India"}, "")
    assert "heuristic" in result["source"].lower()
    assert "live market data" in result["source"].lower() or "cited study" in result["source"].lower()


def test_geography_field_alone_is_enough_to_detect_international_market():
    """Regression guard: market_evidence['geography'] must be scanned even when the founder's
    free-text description never repeats the market — this was previously silently ignored, so a
    US-targeting healthcare startup with geography='United States' would default to INR."""
    result = build_pricing_intelligence(
        _vp(primary_domain="Remote Patient Monitoring"), {"label": "healthcare"},
        {"geography": "United States"}, "An AI platform that helps hospitals predict readmission risk.",
    )
    assert result["currency"] == "USD"
    assert result["target_market"] == "international"
    assert result["target_market_is_assumption"] is False


def test_pricing_tiers_always_present_and_ordered():
    result = build_pricing_intelligence(_vp(), {"label": "b2b"}, {"target_market": "India"}, "")
    tiers = result["pricing_tiers"]
    assert tiers["pilot"] < tiers["launch"] < tiers["premium"]
    assert tiers["recommended_starting_tier"] in ("pilot", "launch")
    assert tiers["starting_tier_reason"]


def test_venture_signals_recommend_launch_tier_when_traction_confirmed():
    no_signals = build_pricing_intelligence(_vp(), {"label": "b2b"}, {"target_market": "India"}, "")
    with_traction = build_pricing_intelligence(
        _vp(), {"label": "b2b"}, {"target_market": "India"}, "",
        venture_signals={"has_traction": True, "has_prototype": True},
    )
    assert no_signals["pricing_tiers"]["recommended_starting_tier"] == "pilot"
    assert with_traction["pricing_tiers"]["recommended_starting_tier"] == "launch"


def test_personalization_references_founders_own_known_competitors():
    result = build_pricing_intelligence(
        _vp(), {"label": "b2b"}, {"target_market": "India"}, "",
        venture_signals={"known_competitors": ["Toast", "Zomato"]},
    )
    assert any("Toast" in note for note in result["personalization"])


def test_no_venture_signals_produces_no_personalization_fabrication():
    result = build_pricing_intelligence(_vp(), {"label": "b2b"}, {"target_market": "India"}, "")
    assert result["personalization"] == []


def test_us_and_uk_abbreviations_are_detected_as_word_boundaries():
    """"the US" / "UK" must be recognized without false-positiving on substrings like "business"
    or "truck"."""
    us_result = build_pricing_intelligence(
        _vp(), {"label": "b2b"}, {}, "A platform that helps hospitals in the US predict risk."
    )
    assert us_result["target_market"] == "international"

    no_false_positive = build_pricing_intelligence(
        _vp(), {"label": "b2b"}, {}, "A business tool that helps truck fleets track fuel usage."
    )
    assert no_false_positive["target_market"] == "india"
    assert no_false_positive["target_market_is_assumption"] is True
