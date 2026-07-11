import pytest

from app.agents.judge import synthesize
from app.ml.funding_readiness import assess_funding_readiness


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
