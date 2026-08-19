"""Tests for the Student 2 deterministic agents: market intelligence, competitor analysis,
customer persona, and business model. Each must never fabricate a fact absent from its inputs —
these tests assert that missing evidence is reported as a gap, not silently invented.
"""

import json

from app.agents.business_model_agent import generate_business_model
from app.agents.competitor_agent import generate_competitor_analysis
from app.agents.customer_persona_agent import generate_customer_persona
from app.agents.market_agent import generate_market_analysis


# --- Market Intelligence Agent -------------------------------------------------------------


def test_market_analysis_flags_missing_evidence_when_nothing_submitted():
    result = generate_market_analysis(industry_prediction=None, funding_assessment={}, market_evidence={})
    assert "target_market" in result["evidence_gaps"]
    assert "geography" in result["evidence_gaps"]
    assert result["confidence"] == "low"


def test_market_analysis_never_invents_a_market_size_number():
    result = generate_market_analysis(
        industry_prediction={"predicted_industry": "fintech", "is_uncertain": False},
        funding_assessment={"breakdown": []},
        market_evidence={"target_market": "SMB payments", "geography": "USA"},
    )
    serialized = json.dumps(result)
    assert "$" not in serialized  # no invented dollar figure anywhere in the output
    assert "billion" not in serialized.lower() and "million" not in serialized.lower()


def test_market_analysis_uses_higher_confidence_with_more_evidence():
    low = generate_market_analysis(industry_prediction=None, funding_assessment={}, market_evidence={})
    high = generate_market_analysis(
        industry_prediction={"predicted_industry": "fintech", "is_uncertain": False},
        funding_assessment={"breakdown": []},
        market_evidence={
            "target_market": "SMBs",
            "geography": "USA",
            "customer_type": "B2B",
            "startup_stage": "growth",
        },
    )
    assert low["confidence"] == "low"
    assert high["confidence"] == "medium"


# --- Competitor Analysis Agent --------------------------------------------------------------


def test_competitor_analysis_echoes_user_named_competitors_as_unverified():
    result = generate_competitor_analysis(known_competitors=["Acme Corp"], industry_prediction=None)
    assert result["entries"][0]["competitor_or_alternative"] == "Acme Corp"
    assert result["entries"][0]["confidence"] == "low"
    assert "not independently verified" in result["entries"][0]["category"]


def test_competitor_analysis_falls_back_to_generic_categories_when_none_named():
    result = generate_competitor_analysis(known_competitors=[], industry_prediction={"predicted_industry": "saas"})
    assert len(result["entries"]) == 3
    for entry in result["entries"]:
        assert "category" in entry["category"] or "categor" in entry["category"]


def test_competitor_analysis_never_invents_a_specific_pricing_or_market_share_number():
    result = generate_competitor_analysis(known_competitors=["Acme Corp"], industry_prediction=None)
    serialized = json.dumps(result).lower()
    # The disclaimer legitimately discusses these concepts by name; what must never appear is an
    # invented numeric figure (a dollar amount or a percentage) attached to them.
    import re

    assert not re.search(r"\$\s?\d", serialized)
    assert not re.search(r"\d+(\.\d+)?\s?%", serialized)


# --- Customer Persona Agent ------------------------------------------------------------------


def test_customer_persona_marks_unknown_fields_when_no_evidence():
    result = generate_customer_persona(market_evidence={}, industry_prediction=None)
    persona = result["personas"][0]
    assert persona["pain_point"] == "unknown — no direct evidence of a specific pain point was submitted"
    assert "pain_point" not in persona["field_provenance"] or persona["field_provenance"]["pain_point"] == "unknown"


def test_customer_persona_never_invents_demographics():
    result = generate_customer_persona(
        market_evidence={"customer_type": "clinic administrators"}, industry_prediction=None
    )
    serialized = json.dumps(result).lower()
    for forbidden in ("age:", "income:", "years old"):
        assert forbidden not in serialized


def test_customer_persona_uses_evidence_backed_customer_type_when_provided():
    result = generate_customer_persona(
        market_evidence={"customer_type": "clinic administrators"}, industry_prediction=None
    )
    persona = result["personas"][0]
    assert persona["customer_type"] == "clinic administrators"
    assert persona["field_provenance"]["role_or_context"].startswith("evidence-backed")


# --- Business Model Agent --------------------------------------------------------------------


def test_business_model_marks_missing_revenue_streams_when_no_assumptions():
    result = generate_business_model(
        startup_description="A tool for X.",
        market_evidence={},
        revenue_estimate={"available": False},
        funding_assessment={"breakdown": []},
    )
    assert "unknown" in result["revenue_streams"]
    assert "revenue_streams" in result["evidence_gaps"]


def test_business_model_never_invents_cac_or_ltv_numbers():
    result = generate_business_model(
        startup_description="A tool for X.",
        market_evidence={},
        revenue_estimate={"available": False},
        funding_assessment={"breakdown": []},
    )
    serialized = json.dumps(result).lower()
    assert "cac:" not in serialized
    assert "ltv:" not in serialized


def test_business_model_value_proposition_is_first_sentence_of_description():
    result = generate_business_model(
        startup_description="A telehealth platform for chronic care. It connects patients with clinicians.",
        market_evidence={},
        revenue_estimate={"available": False},
        funding_assessment={"breakdown": []},
    )
    assert result["value_proposition"] == "A telehealth platform for chronic care."
