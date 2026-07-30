import pytest

from app.agents.alternative_explanation_engine import build_alternative_explanation_set
from app.agents.contradiction_engine import build_contradiction_set
from app.agents.evidence_ledger import build_evidence_ledger
from app.agents.hypothesis_set import build_hypothesis_set
from app.agents.venture_frame import build_venture_frame
from app.ml.funding_readiness import assess_funding_readiness


def _pipeline(
    startup_description="",
    industry_prediction=None,
    venture_positioning=None,
    market_evidence=None,
    funding_answers=None,
    business_model=None,
    competitor_analysis=None,
):
    funding_assessment = assess_funding_readiness(funding_answers or {})
    evidence_ledger = build_evidence_ledger(funding_assessment, market_evidence, industry_prediction)
    venture_frame = build_venture_frame(
        startup_name="Test",
        startup_description=startup_description,
        funding_assessment=funding_assessment,
        industry_prediction=industry_prediction,
        venture_positioning=venture_positioning,
        market_evidence=market_evidence,
        business_model=business_model,
        competitor_analysis=competitor_analysis,
    )
    hypothesis_set = build_hypothesis_set(venture_frame, evidence_ledger, funding_assessment)
    contradiction_set = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    return evidence_ledger, venture_frame, hypothesis_set, contradiction_set


REQUIRED_KEYS = {
    "id", "category", "title", "description", "confidence", "supporting_evidence_ids",
    "contradicting_evidence_ids", "assumptions", "why_primary_may_be_incomplete",
    "distinguishing_evidence", "recommended_experiment", "expected_outcome_if_true",
    "expected_outcome_if_false", "primary_explanation_id",
}


# --- empty / one-line ideas ------------------------------------------------------------------


def test_empty_idea_produces_no_crash_and_no_fabricated_alternatives():
    args = _pipeline()
    result = build_alternative_explanation_set(*args)
    assert result["alternative_explanation_engine_version"] == "v1"
    assert result["alternative_explanations"] == []


def test_one_line_idea_with_no_ambiguity_produces_no_alternatives():
    args = _pipeline(startup_description="A tool for small businesses.", funding_answers={"problem_clarity": 2})
    result = build_alternative_explanation_set(*args)
    assert result["alternative_explanations"] == []
    # Self-challenge is recorded explicitly rather than silently omitted.
    assert result["categories_with_single_explanation"]


# --- ambiguous positioning / industry produces a genuine alternative -------------------------


def test_ambiguous_industry_prediction_produces_one_alternative_with_full_schema():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    args = _pipeline(industry_prediction=industry_prediction)
    result = build_alternative_explanation_set(*args)
    alts = result["alternative_explanations"]
    assert len(alts) == 1
    item = alts[0]
    assert REQUIRED_KEYS.issubset(item.keys())
    assert item["category"] == "industry_contradiction"
    assert 0.0 <= item["confidence"] <= 1.0
    assert item["supporting_evidence_ids"]
    assert item["primary_explanation_id"]
    assert "fintech" in item["title"].lower() or "fintech" in item["description"].lower()


def test_confident_industry_prediction_never_fabricates_an_alternative():
    industry_prediction = {"predicted_industry": "saas", "confidence": 0.95, "is_uncertain": False, "alternatives": []}
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2})
    result = build_alternative_explanation_set(*args)
    assert result["alternative_explanations"] == []


# --- never fake balance: single-explanation categories say so explicitly ---------------------


def test_single_hypothesis_categories_are_recorded_not_fabricated():
    args = _pipeline(
        funding_answers={"traction": 2},
        market_evidence={"customer_type": "SMB owners"},
    )
    result = build_alternative_explanation_set(*args)
    assert result["alternative_explanations"] == []
    categories = {c["category"] for c in result["categories_with_single_explanation"]}
    assert "target_customer" in categories
    for entry in result["categories_with_single_explanation"]:
        assert entry["leading_explanation"]
        assert entry["note"]


# --- stage-gated traction alternative ("too early to measure") -------------------------------


def test_early_stage_traction_gap_produces_too_early_alternative():
    args = _pipeline(
        funding_answers={"traction": {"state": "confirmed_negative"}},
        market_evidence={"startup_stage": "idea"},
    )
    result = build_alternative_explanation_set(*args)
    ids = {a["id"] for a in result["alternative_explanations"]}
    assert "major_risk:too_early_to_measure:alternative" in ids
    item = next(a for a in result["alternative_explanations"] if a["id"] == "major_risk:too_early_to_measure:alternative")
    assert REQUIRED_KEYS.issubset(item.keys())
    assert "major_risk" not in {c["category"] for c in result["categories_with_single_explanation"]}


def test_growth_stage_traction_gap_does_not_produce_too_early_alternative():
    args = _pipeline(
        funding_answers={"traction": {"state": "confirmed_negative"}},
        market_evidence={"startup_stage": "growth"},
    )
    result = build_alternative_explanation_set(*args)
    ids = {a["id"] for a in result["alternative_explanations"]}
    assert "major_risk:too_early_to_measure:alternative" not in ids


def test_no_venture_stage_supplied_does_not_produce_too_early_alternative():
    args = _pipeline(funding_answers={"traction": {"state": "confirmed_negative"}})
    result = build_alternative_explanation_set(*args)
    ids = {a["id"] for a in result["alternative_explanations"]}
    assert "major_risk:too_early_to_measure:alternative" not in ids


def test_confirmed_positive_traction_never_produces_too_early_alternative():
    args = _pipeline(
        funding_answers={"traction": {"state": "confirmed_positive", "severity": 2}},
        market_evidence={"startup_stage": "idea"},
    )
    result = build_alternative_explanation_set(*args)
    ids = {a["id"] for a in result["alternative_explanations"]}
    assert "major_risk:too_early_to_measure:alternative" not in ids


# --- false positives: plural/singular, differing specificity ---------------------------------


def test_plural_singular_variants_never_produce_an_alternative():
    industry_prediction = {"predicted_industry": "Restaurant", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    venture_positioning = {
        "primary_domain": "restaurant",
        "confidence": 0.9,
        "is_low_confidence": False,
        "resolution_source": "taxonomy",
        "secondary_domains": [],
    }
    args = _pipeline(industry_prediction=industry_prediction, venture_positioning=venture_positioning)
    result = build_alternative_explanation_set(*args)
    assert result["alternative_explanations"] == []


def test_healthcare_and_clinical_decision_support_do_not_produce_a_fabricated_alternative():
    industry_prediction = {"predicted_industry": "healthcare", "confidence": 0.85, "is_uncertain": False, "alternatives": []}
    venture_positioning = {
        "primary_domain": "Clinical Decision Support",
        "confidence": 0.8,
        "is_low_confidence": False,
        "resolution_source": "taxonomy",
        "secondary_domains": [],
    }
    args = _pipeline(industry_prediction=industry_prediction, venture_positioning=venture_positioning)
    result = build_alternative_explanation_set(*args)
    assert result["alternative_explanations"] == []


# --- multi-domain sweep ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "domain",
    ["healthcare", "artificial intelligence", "fintech", "marketplace", "hardware", "education", "consumer", "social impact"],
)
def test_domain_sweep_never_crashes(domain):
    industry_prediction = {"predicted_industry": domain, "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    args = _pipeline(
        startup_description=f"A venture in {domain}.",
        industry_prediction=industry_prediction,
        funding_answers={"problem_clarity": 2},
    )
    result = build_alternative_explanation_set(*args)
    assert isinstance(result["alternative_explanations"], list)


# --- weak / strong / mixed evidence -----------------------------------------------------------


def test_weak_evidence_still_produces_a_valid_schema_when_ambiguous():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.31,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.29}],
    }
    args = _pipeline(industry_prediction=industry_prediction)
    result = build_alternative_explanation_set(*args)
    for item in result["alternative_explanations"]:
        assert 0.0 <= item["confidence"] <= 1.0


# --- determinism / idempotence -----------------------------------------------------------------


def test_build_alternative_explanation_set_is_deterministic():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2})
    first = build_alternative_explanation_set(*args)
    second = build_alternative_explanation_set(*args)
    assert first == second


def test_all_none_inputs_handled_safely():
    result = build_alternative_explanation_set(None, None, None, None)
    assert result["alternative_explanations"] == []
    assert result["categories_with_single_explanation"] == []


# --- no duplicated explanations ------------------------------------------------------------------


def test_no_duplicate_alternative_ids():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    args = _pipeline(
        industry_prediction=industry_prediction,
        funding_answers={"traction": {"state": "confirmed_negative"}},
        market_evidence={"startup_stage": "idea"},
    )
    result = build_alternative_explanation_set(*args)
    ids = [a["id"] for a in result["alternative_explanations"]]
    assert len(ids) == len(set(ids))


# --- evidence linkage / confidence propagation ----------------------------------------------------


def test_every_alternative_links_real_evidence_ids_from_the_ledger():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    evidence_ledger, venture_frame, hypothesis_set, contradiction_set = _pipeline(industry_prediction=industry_prediction)
    ledger_ids = {item["id"] for item in evidence_ledger}
    result = build_alternative_explanation_set(evidence_ledger, venture_frame, hypothesis_set, contradiction_set)
    for item in result["alternative_explanations"]:
        for evidence_id in item["supporting_evidence_ids"]:
            assert evidence_id in ledger_ids
