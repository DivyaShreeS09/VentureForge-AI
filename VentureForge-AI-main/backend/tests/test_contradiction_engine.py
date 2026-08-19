import pytest

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
    return evidence_ledger, venture_frame, hypothesis_set


# --- empty / one-line ideas -----------------------------------------------------------------


def test_empty_idea_produces_no_crash_and_empty_or_minimal_contradictions():
    evidence_ledger, venture_frame, hypothesis_set = _pipeline()
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    assert result["contradiction_engine_version"] == "v1"
    assert isinstance(result["contradictions"], list)
    # No ambiguity possible with zero upstream signals.
    assert result["counts_by_kind"].get("ambiguity", 0) == 0


def test_one_line_idea_with_no_industry_or_positioning_has_no_ambiguity():
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(
        startup_description="A tool for small businesses.",
        funding_answers={"problem_clarity": 2},
    )
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    assert result["counts_by_kind"].get("ambiguity", 0) == 0


# --- contradictory industry (ambiguity kind) ------------------------------------------------


def test_ambiguous_industry_prediction_produces_ambiguity_contradiction():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(industry_prediction=industry_prediction)
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    industry_items = [c for c in result["contradictions"] if c["category"] == "industry_contradiction"]
    assert len(industry_items) == 1
    item = industry_items[0]
    assert item["kind"] == "ambiguity"
    assert 0.0 < item["confidence"] <= 1.0
    assert item["supporting_evidence_ids"]
    assert item["conflicting_evidence_ids"]
    assert "saas" in item["description"] or "fintech" in item["description"]
    assert "conflict" not in item["description"].lower()  # never accusatory phrasing


def test_confident_industry_prediction_produces_no_ambiguity():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.95,
        "is_uncertain": False,
        "alternatives": [{"industry": "fintech", "confidence": 0.1}],
    }
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(industry_prediction=industry_prediction)
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    assert result["counts_by_kind"].get("ambiguity", 0) == 0


# --- false positives: plural/singular, synonyms, differing specificity ---------------------


def test_plural_singular_variants_never_treated_as_contradictory():
    # Industry classifier and positioning both effectively agree in different casing/spacing;
    # hypothesis_set's own label-merge already prevents this from ever reaching this engine as a
    # conflict.
    industry_prediction = {"predicted_industry": "Restaurant", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    venture_positioning = {
        "primary_domain": "restaurant",
        "confidence": 0.9,
        "is_low_confidence": False,
        "resolution_source": "taxonomy",
        "secondary_domains": [],
    }
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(
        industry_prediction=industry_prediction, venture_positioning=venture_positioning
    )
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    assert result["counts_by_kind"].get("ambiguity", 0) == 0


def test_healthcare_and_clinical_decision_support_do_not_contradict():
    industry_prediction = {"predicted_industry": "healthcare", "confidence": 0.85, "is_uncertain": False, "alternatives": []}
    venture_positioning = {
        "primary_domain": "Clinical Decision Support",
        "confidence": 0.8,
        "is_low_confidence": False,
        "resolution_source": "taxonomy",
        "secondary_domains": [],
    }
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(
        industry_prediction=industry_prediction, venture_positioning=venture_positioning
    )
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    # Neither is flagged ambiguous by its own resolver, so no contradiction is fabricated merely
    # because the labels differ in specificity.
    assert result["counts_by_kind"].get("ambiguity", 0) == 0


# --- missing information (distinct kind, never collapsed into contradiction) ----------------


def test_missing_information_present_for_unanswered_dimensions():
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(funding_answers={"problem_clarity": 2})
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    missing = [c for c in result["contradictions"] if c["kind"] == "missing_information"]
    assert missing
    for item in missing:
        assert item["category"] == "missing_information"
        assert item["confidence"] == 1.0
        assert item["severity"] == "low"


def test_missing_information_never_labeled_ambiguity_or_true_contradiction():
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(funding_answers={})
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    kinds = {c["kind"] for c in result["contradictions"]}
    assert kinds.issubset({"ambiguity", "missing_information", "true_contradiction", "evolution"})
    missing = [c for c in result["contradictions"] if c["kind"] == "missing_information"]
    assert all(c["kind"] != "ambiguity" for c in missing)


# --- readiness / traction / revenue evidence states, exercised through the pipeline ---------


def test_contradictory_readiness_evidence_does_not_crash_and_stays_well_formed():
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(
        funding_answers={
            "traction": {"state": "confirmed_negative"},
            "revenue_model_clarity": {"state": "confirmed_positive", "severity": 2},
        }
    )
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    for item in result["contradictions"]:
        assert item["id"]
        assert item["category"]
        assert item["kind"] in ("ambiguity", "missing_information", "true_contradiction", "evolution")
        assert isinstance(item["supporting_evidence_ids"], list)
        assert isinstance(item["conflicting_evidence_ids"], list)
        assert isinstance(item["possible_explanations"], list) and item["possible_explanations"]
        assert item["recommended_investigation"]


# --- domain sweep: healthcare, AI, fintech, marketplaces, hardware, education, social impact -


@pytest.mark.parametrize(
    "domain",
    ["healthcare", "artificial intelligence", "fintech", "marketplace", "hardware", "education", "social impact"],
)
def test_domain_sweep_never_crashes_and_never_fabricates_ambiguity_from_a_confident_single_source(domain):
    industry_prediction = {"predicted_industry": domain, "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(
        startup_description=f"A venture in {domain}.",
        industry_prediction=industry_prediction,
        funding_answers={"problem_clarity": 2},
    )
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    assert result["counts_by_kind"].get("ambiguity", 0) == 0


# --- determinism -----------------------------------------------------------------------------


def test_build_contradiction_set_is_deterministic():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(
        industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2}
    )
    first = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    second = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    assert first == second


def test_build_contradiction_set_handles_all_none_inputs_safely():
    result = build_contradiction_set(None, None, None)
    assert result["contradictions"] == []
    assert result["counts_by_kind"] == {}


# --- schema shape -----------------------------------------------------------------------------


def test_every_contradiction_has_the_full_required_shape():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    evidence_ledger, venture_frame, hypothesis_set = _pipeline(
        industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2}
    )
    result = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    required_keys = {
        "id", "category", "kind", "title", "description", "severity", "confidence",
        "supporting_evidence_ids", "conflicting_evidence_ids", "affected_modules",
        "recommended_investigation", "possible_explanations",
    }
    for item in result["contradictions"]:
        assert required_keys.issubset(item.keys())
        assert item["severity"] in ("low", "medium", "high")
        assert 0.0 <= item["confidence"] <= 1.0
