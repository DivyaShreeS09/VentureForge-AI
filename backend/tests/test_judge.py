import pytest

from app.agents.judge import synthesize
from app.ml.funding_readiness import DIMENSIONS, assess_funding_readiness


def test_missing_funding_assessment_raises():
    with pytest.raises(ValueError):
        synthesize({"predicted_industry": "saas", "confidence": 0.9}, {}, {"low_confidence": False, "notes": []})


def test_low_confidence_flagged():
    funding = assess_funding_readiness({"problem_clarity": 2})
    result = synthesize(
        {"predicted_industry": "saas", "confidence": 0.2},
        funding,
        {"low_confidence": True, "notes": ["low confidence note"]},
    )
    assert result["confidence_level"] == "low"


def test_strengths_and_weaknesses_from_breakdown():
    funding = assess_funding_readiness(
        {
            "problem_clarity": 2,
            "customer_pain_evidence": 0,
            "market_size_evidence": 1,
        }
    )
    result = synthesize(
        {"predicted_industry": "fintech", "confidence": 0.8},
        funding,
        {"low_confidence": False, "notes": []},
    )
    assert any("Problem Clarity" in s for s in result["strengths"])
    assert any("Customer Pain" in w for w in result["weaknesses"])


def test_no_industry_prediction_is_disclosed_not_hidden():
    funding = assess_funding_readiness({"problem_clarity": 2})
    result = synthesize(None, funding, {"low_confidence": True, "notes": []})
    assert "not classified" in result["overall_assessment"]


def test_never_fabricates_missing_evidence_dimensions():
    funding = assess_funding_readiness({"problem_clarity": 2})
    result = synthesize({"predicted_industry": "saas", "confidence": 0.9}, funding, {"low_confidence": False, "notes": []})
    # Every missing_evidence label must correspond to a real rubric dimension label.
    all_labels = {b["label"] for b in funding["breakdown"]}
    assert set(result["missing_evidence"]).issubset(all_labels)


# --- Four explicit evidence states drive strengths/weaknesses/hypotheses (Phase 0) -------------


def test_not_sure_yet_never_becomes_a_weakness():
    funding = assess_funding_readiness(
        {
            "problem_clarity": {"state": "not_sure_yet"},
            "traction": {"state": "not_sure_yet"},
        }
    )
    result = synthesize({"predicted_industry": "saas", "confidence": 0.9}, funding, {"low_confidence": False, "notes": []})
    assert result["weaknesses"] == []


def test_confirmed_negative_does_become_a_weakness():
    funding = assess_funding_readiness({"traction": {"state": "confirmed_negative"}})
    result = synthesize({"predicted_industry": "saas", "confidence": 0.9}, funding, {"low_confidence": False, "notes": []})
    assert any("Traction" in w for w in result["weaknesses"])


def test_every_not_sure_yet_field_produces_a_structured_hypothesis():
    other_dims = {
        name: {"state": "not_applicable"}
        for name in DIMENSIONS
        if name not in ("traction", "revenue_model_clarity")
    }
    funding = assess_funding_readiness(
        {
            **other_dims,
            "traction": {"state": "not_sure_yet"},
            "revenue_model_clarity": {"state": "not_sure_yet"},
        }
    )
    result = synthesize({"predicted_industry": "saas", "confidence": 0.9}, funding, {"low_confidence": False, "notes": []})
    dims = {h["source_dimension"] for h in result["suggested_possibilities"]}
    assert dims == {"traction", "revenue_model_clarity"}
    for h in result["suggested_possibilities"]:
        assert h["starting_hypothesis"]
        assert h["validation_task"]


def test_not_applicable_dimension_has_no_weakness_and_no_hypothesis():
    other_dims = {name: {"state": "confirmed_positive", "severity": 2} for name in DIMENSIONS if name != "traction"}
    funding = assess_funding_readiness({**other_dims, "traction": {"state": "not_applicable"}})
    result = synthesize({"predicted_industry": "saas", "confidence": 0.9}, funding, {"low_confidence": False, "notes": []})
    assert result["weaknesses"] == []
    assert result["suggested_possibilities"] == []


def test_malformed_or_absent_evidence_handled_safely():
    # No funding_answers submitted at all, and a directly-malformed breakdown entry — neither
    # should raise or fabricate a weakness/strength.
    funding = assess_funding_readiness({})
    result = synthesize(None, funding, {"low_confidence": True, "notes": []})
    assert result["weaknesses"] == []
    assert len(result["suggested_possibilities"]) == len(funding["missing_evidence"])


# --- founder_guidance_items (Phase 1 mentor-language correction) -------------------------------


def test_founder_guidance_items_present_and_never_confirmed_risk():
    funding = assess_funding_readiness(
        {
            "traction": {"state": "confirmed_negative"},
            "revenue_model_clarity": {"state": "confirmed_negative"},
            "team_completeness": {"state": "confirmed_negative"},
        }
    )
    result = synthesize({"predicted_industry": "saas", "confidence": 0.9}, funding, {"low_confidence": False, "notes": []})
    items = result["founder_guidance_items"]
    assert items, "expected at least one founder_guidance_item"
    assert all(item["category"] != "confirmed_risk" for item in items)
    by_dim = {item["dimension"]: item for item in items}
    # Stage-aware examples from the corrected plan.
    assert by_dim["traction"]["category"] == "validation_opportunity"
    assert by_dim["revenue_model_clarity"]["category"] == "discovery_question"
    assert by_dim["team_completeness"]["category"] == "improvement_opportunity"


def test_uncertain_success_prediction_never_appended_to_weaknesses():
    """Phase 1 correction: a heavily-imputed/near-chance historical pattern signal must never
    read as a founder-facing risk (see app.ml.success_predictor's founder-facing band)."""
    funding = assess_funding_readiness({"problem_clarity": 2})
    result = synthesize(
        {"predicted_industry": "saas", "confidence": 0.9},
        funding,
        {"low_confidence": False, "notes": []},
        success_prediction={"is_uncertain": True, "success_probability": 0.51, "model_pipeline": "x", "model_version": "v1"},
    )
    assert result["weaknesses"] == []
    assert not any("uncertain" in w.lower() for w in result["weaknesses"])
