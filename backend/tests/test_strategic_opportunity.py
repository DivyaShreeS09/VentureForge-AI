"""Deterministic Strategic Opportunity Discovery baseline tests (Phase 3). No network — see
test_strategic_opportunity_reviewer.py for the Gemini-additive layer.
"""

from app.agents.strategic_opportunity import build_deterministic_strategic_opportunity

_VENTURE_POSITIONING = {
    "primary_domain": "Smart Facilities Technology",
    "secondary_domains": ["PropTech"],
    "deployment_sectors": ["Campuses", "Hotels"],
}
_MARKET_INTELLIGENCE = {"market_summary": "Targets facilities managers at campuses and hotels."}
_CUSTOMER_PERSONAS = {"personas": [{"persona_name": "Facilities Manager", "role_or_context": "facilities managers"}]}
_BUSINESS_MODEL = {"revenue_streams": "Per-building monthly subscription"}
_COMPETITOR_ANALYSIS = {"verified_competitors": []}
_FEATURE_GAP = {
    "present_capabilities": [{"id": "real_time_utility_monitoring", "label": "Real-Time Utility Monitoring"}],
    "recommended_capabilities": [],
    "premature_capabilities": [
        {"id": "predictive_maintenance", "label": "Predictive Maintenance", "prerequisites": ["anomaly_alerting"]}
    ],
    "not_relevant_capabilities": [],
}
_FOUNDER_GUIDANCE_ITEMS = [
    {"dimension": "traction", "category": "strength", "title": "Traction confirmed.", "next_step": "Keep validating."},
]
_FUNDING_ASSESSMENT = {"level": "developing"}


def _build(**overrides):
    kwargs = dict(
        venture_positioning=_VENTURE_POSITIONING,
        market_intelligence=_MARKET_INTELLIGENCE,
        customer_personas=_CUSTOMER_PERSONAS,
        business_model=_BUSINESS_MODEL,
        competitor_analysis=_COMPETITOR_ANALYSIS,
        feature_gap=_FEATURE_GAP,
        founder_guidance_items=_FOUNDER_GUIDANCE_ITEMS,
        funding_assessment=_FUNDING_ASSESSMENT,
    )
    kwargs.update(overrides)
    return build_deterministic_strategic_opportunity(**kwargs)


def test_returns_all_four_sections():
    result = _build()
    for key in ("primary_opportunity", "adjacent_opportunities", "future_expansion", "strategic_risks"):
        assert key in result
    assert result["source"] == "deterministic"
    assert result["strategic_opportunity_version"] == "v1"


def test_primary_opportunity_includes_all_six_reasoning_dimensions():
    result = _build()
    primary = result["primary_opportunity"]
    for field in ("demand", "buyer", "urgency", "willingness_to_pay", "competition", "implementation_difficulty"):
        assert field in primary
    assert primary["opportunity"] == "Smart Facilities Technology"
    assert primary["source"] == "deterministic"


def test_primary_opportunity_is_confirmed_when_demand_buyer_and_traction_present():
    result = _build()
    assert result["primary_opportunity"]["confidence_tier"] == "confirmed_from_evidence"


def test_primary_opportunity_downgrades_to_hypothesis_with_weak_evidence():
    result = _build(market_intelligence=None, customer_personas=None, founder_guidance_items=[])
    assert result["primary_opportunity"]["confidence_tier"] == "reasonable_hypothesis"


def test_adjacent_opportunities_explain_shared_workflow_not_just_name_the_market():
    result = _build()
    assert len(result["adjacent_opportunities"]) >= 3
    for item in result["adjacent_opportunities"]:
        assert len(item["reason"]) > 20  # a real explanation, not a bare label
        assert item["confidence_tier"] == "reasonable_hypothesis"
        assert item["source"] == "deterministic"
    titles = [i["opportunity"] for i in result["adjacent_opportunities"]]
    assert "Hospitals" in titles
    assert "Hotels" in titles


def test_unknown_domain_falls_back_to_generic_adjacent_reasoning():
    result = _build(venture_positioning={"primary_domain": "Some Unlisted Domain", "secondary_domains": [], "deployment_sectors": []})
    assert len(result["adjacent_opportunities"]) == 1
    assert "adjacent teams" in result["adjacent_opportunities"][0]["opportunity"].lower()


def test_future_expansion_covers_all_six_forms():
    result = _build()
    opportunities = {i["opportunity"] for i in result["future_expansion"]}
    assert opportunities == {"Platform", "Marketplace", "Developer API", "Enterprise Suite", "Analytics Platform", "Compliance Platform"}
    assert all(i["confidence_tier"] in ("reasonable_hypothesis", "speculative_future_opportunity") for i in result["future_expansion"])
    assert all(i["confidence_tier"] != "confirmed_from_evidence" for i in result["future_expansion"])


def test_future_expansion_platform_is_hypothesis_when_multi_sector_signal_present():
    result = _build()  # 2 deployment sectors
    platform = next(i for i in result["future_expansion"] if i["opportunity"] == "Platform")
    assert platform["confidence_tier"] == "reasonable_hypothesis"


def test_future_expansion_platform_is_speculative_with_single_sector():
    result = _build(venture_positioning={**_VENTURE_POSITIONING, "deployment_sectors": ["Campuses"]})
    platform = next(i for i in result["future_expansion"] if i["opportunity"] == "Platform")
    assert platform["confidence_tier"] == "speculative_future_opportunity"


def test_strategic_risks_cover_all_six_categories_or_a_reasonable_subset():
    result = _build()
    categories = {r["category"] for r in result["strategic_risks"]}
    assert categories.issubset({"market", "timing", "regulatory", "technology", "competition", "adoption"})
    assert "market" in categories
    assert "timing" in categories
    for risk in result["strategic_risks"]:
        for field in ("why", "likelihood", "impact", "mitigation", "confidence_tier"):
            assert field in risk


def test_regulatory_risk_is_confirmed_and_elevated_for_health_domains():
    result = _build(venture_positioning={"primary_domain": "HealthTech Diagnostics", "secondary_domains": [], "deployment_sectors": ["Clinics"]})
    regulatory = next(r for r in result["strategic_risks"] if r["category"] == "regulatory")
    assert regulatory["confidence_tier"] == "confirmed_from_evidence"
    assert regulatory["likelihood"] == "high"


def test_regulatory_risk_is_low_for_non_health_domains():
    result = _build()
    regulatory = next(r for r in result["strategic_risks"] if r["category"] == "regulatory")
    assert regulatory["likelihood"] == "low"


def test_regulatory_risk_elevated_from_description_keywords_not_just_taxonomy_domain():
    result = _build(startup_description="We underwrite pet insurance policies sold directly to consumers.")
    regulatory = next(r for r in result["strategic_risks"] if r["category"] == "regulatory")
    assert regulatory["confidence_tier"] == "confirmed_from_evidence"
    assert regulatory["likelihood"] == "high"
    assert "regulated industry" in regulatory["risk"].lower()


def test_technology_risk_present_when_premature_capabilities_exist():
    result = _build()
    tech_risks = [r for r in result["strategic_risks"] if r["category"] == "technology"]
    assert tech_risks
    assert "Predictive Maintenance" in tech_risks[0]["why"]


def test_no_technology_risk_when_no_premature_capabilities():
    result = _build(feature_gap={**_FEATURE_GAP, "premature_capabilities": []})
    tech_risks = [r for r in result["strategic_risks"] if r["category"] == "technology"]
    assert tech_risks == []


def test_competition_risk_reflects_named_competitors():
    result = _build(competitor_analysis={"verified_competitors": [{"name": "Acme Facilities"}]})
    competition = next(r for r in result["strategic_risks"] if r["category"] == "competition")
    assert competition["confidence_tier"] == "confirmed_from_evidence"
    assert "Acme Facilities" in competition["why"]


def test_strategic_risks_are_never_framed_as_founder_weaknesses():
    result = _build()
    for risk in result["strategic_risks"]:
        assert "weakness" not in risk["why"].lower()
        assert "weakness" not in risk["risk"].lower()


def test_never_touches_authoritative_inputs():
    # The function takes venture_positioning/funding_assessment as read-only inputs and must
    # never mutate them.
    positioning_copy = dict(_VENTURE_POSITIONING)
    funding_copy = dict(_FUNDING_ASSESSMENT)
    _build()
    assert _VENTURE_POSITIONING == positioning_copy
    assert _FUNDING_ASSESSMENT == funding_copy
