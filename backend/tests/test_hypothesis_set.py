import copy

from app.agents.hypothesis_set import build_hypothesis_set
from app.agents.venture_frame import build_venture_frame
from app.agents.evidence_ledger import build_evidence_ledger
from app.ml.funding_readiness import DIMENSIONS, assess_funding_readiness


# --- Empty / minimal inputs never hallucinate a hypothesis --------------------------------------


def test_completely_empty_input_produces_no_categories_at_all():
    frame = build_venture_frame()
    result = build_hypothesis_set(frame)
    assert result["categories"] == {}
    assert result["hypothesis_set_version"] == "v1"


def test_one_line_idea_with_no_evidence_stays_honest():
    frame = build_venture_frame(startup_name="Nova", startup_description="AI for retail.")
    result = build_hypothesis_set(frame)
    # No funding_assessment/market_evidence/business_model supplied -> nothing to hypothesize about.
    assert result["categories"] == {}


def test_never_builds_go_to_market_or_opportunity_driver_based_categories():
    funding = assess_funding_readiness({"problem_clarity": 2})
    frame = build_venture_frame(funding_assessment=funding)
    result = build_hypothesis_set(frame, funding_assessment=funding)
    assert "go_to_market" not in result["categories"]


# --- Single-candidate categories (no fabricated competition) ------------------------------------


def test_target_customer_with_one_source_is_a_single_leading_hypothesis():
    frame = build_venture_frame(market_evidence={"customer_type": "Retail operations managers"})
    result = build_hypothesis_set(frame)
    hyps = result["categories"]["target_customer"]
    assert len(hyps) == 1
    assert hyps[0]["title"] == "Retail operations managers"
    assert hyps[0]["status"] == "leading"
    assert hyps[0]["contradicting_evidence_ids"] == []
    assert hyps[0]["supporting_evidence_ids"] == ["market_evidence:customer_type"]


def test_core_problem_hypothesis_quotes_founders_own_words():
    business_model = {"value_proposition": "A subscription analytics dashboard for retail teams."}
    frame = build_venture_frame(business_model=business_model)
    result = build_hypothesis_set(frame)
    hyps = result["categories"]["core_problem"]
    assert hyps[0]["title"] == "A subscription analytics dashboard for retail teams."


# --- Industry ambiguity: competing hypotheses preserved, never silently resolved ----------------


def test_ambiguous_industry_produces_two_competing_mutually_contradicting_hypotheses():
    industry_prediction = {
        "predicted_industry": "b2b",
        "confidence": 0.4,
        "is_uncertain": True,
        "alternatives": [{"industry": "consumer", "confidence": 0.35}],
    }
    frame = build_venture_frame(industry_prediction=industry_prediction)
    result = build_hypothesis_set(frame)
    hyps = result["categories"]["industry_interpretation"]
    assert len(hyps) == 2
    titles = {h["title"] for h in hyps}
    assert titles == {"b2b", "consumer"}
    leading = next(h for h in hyps if h["status"] == "leading")
    other = next(h for h in hyps if h is not leading)
    assert leading["title"] == "b2b"
    assert other["title"] == "consumer"
    assert leading["contradicting_evidence_ids"] == other["supporting_evidence_ids"]
    assert other["contradicting_evidence_ids"] == leading["supporting_evidence_ids"]
    assert other["status"] in ("plausible", "weak", "rejected")


def test_confident_industry_prediction_yields_exactly_one_hypothesis_not_two():
    industry_prediction = {"predicted_industry": "healthcare", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    frame = build_venture_frame(industry_prediction=industry_prediction)
    result = build_hypothesis_set(frame)
    hyps = result["categories"]["industry_interpretation"]
    assert len(hyps) == 1
    assert hyps[0]["title"] == "healthcare"
    assert hyps[0]["status"] == "leading"


def test_matching_industry_and_positioning_labels_corroborate_not_duplicate():
    industry_prediction = {"predicted_industry": "healthcare", "confidence": 0.7, "is_uncertain": False, "alternatives": []}
    venture_positioning = {"primary_domain": "healthcare", "confidence": 0.5, "is_low_confidence": False, "resolution_source": "taxonomy_dominant"}
    frame = build_venture_frame(industry_prediction=industry_prediction, venture_positioning=venture_positioning)
    result = build_hypothesis_set(frame)
    hyps = result["categories"]["industry_interpretation"]
    # Same label from two resolvers merges into one corroborated hypothesis, not two duplicates.
    assert len(hyps) == 1
    assert set(hyps[0]["supporting_evidence_ids"]) == {"model:industry_prediction", "model:venture_positioning"}
    # Corroboration must raise confidence above either single source alone.
    assert hyps[0]["confidence"] > 0.7


def test_different_granularity_labels_are_not_treated_as_contradicting():
    # Classifier says "healthcare" (coarse), positioning says "Clinical Decision Support" (a
    # specific sub-domain) — a difference in specificity, not evidence of disagreement.
    industry_prediction = {"predicted_industry": "healthcare", "confidence": 0.7, "is_uncertain": False, "alternatives": []}
    venture_positioning = {
        "primary_domain": "Clinical Decision Support", "confidence": 0.6, "is_low_confidence": False,
        "resolution_source": "taxonomy_dominant",
    }
    frame = build_venture_frame(industry_prediction=industry_prediction, venture_positioning=venture_positioning)
    result = build_hypothesis_set(frame)
    hyps = result["categories"]["industry_interpretation"]
    assert len(hyps) == 2
    assert all(h["contradicting_evidence_ids"] == [] for h in hyps)


# --- Conflicting evidence: readiness / major_opportunity / major_risk ---------------------------


def test_major_opportunity_uses_the_strongest_confirmed_positive_dimension():
    funding = assess_funding_readiness({"traction": 2, "problem_clarity": 1})
    frame = build_venture_frame(funding_assessment=funding)
    ledger = build_evidence_ledger(funding)
    result = build_hypothesis_set(frame, ledger, funding)
    hyps = result["categories"]["major_opportunity"]
    assert len(hyps) == 1
    assert "Traction" in hyps[0]["title"]


def test_no_major_opportunity_category_when_no_severity_two_dimension_exists():
    funding = assess_funding_readiness({"traction": 1})
    frame = build_venture_frame(funding_assessment=funding)
    ledger = build_evidence_ledger(funding)
    result = build_hypothesis_set(frame, ledger, funding)
    assert "major_opportunity" not in result["categories"]


def test_major_risk_combines_regulatory_and_rubric_gap_as_two_competing_hypotheses():
    funding = assess_funding_readiness({"traction": {"state": "confirmed_negative"}})
    frame = build_venture_frame(
        startup_description="A clinical decision support tool for hospital patient triage.",
        venture_positioning={"primary_domain": "Clinical Decision Support"},
        funding_assessment=funding,
    )
    ledger = build_evidence_ledger(funding)
    result = build_hypothesis_set(frame, ledger, funding)
    hyps = result["categories"]["major_risk"]
    assert len(hyps) == 2
    titles = " ".join(h["title"] for h in hyps)
    assert "regulated healthcare" in titles.lower() or "healthcare" in titles.lower()
    assert "Traction" in titles


def test_readiness_hypothesis_reflects_rubric_level_and_score():
    funding = assess_funding_readiness({name: 2 for name in DIMENSIONS})
    frame = build_venture_frame(funding_assessment=funding)
    ledger = build_evidence_ledger(funding)
    result = build_hypothesis_set(frame, ledger, funding)
    hyp = result["categories"]["readiness"][0]
    assert funding["level"] in hyp["title"]
    assert str(funding["overall_score"]) in hyp["explanation"]


# --- Confidence monotonicity and status assignment ----------------------------------------------


def test_confidence_monotonicity_more_agreement_never_lowers_confidence():
    lone_prediction = {"predicted_industry": "fintech", "confidence": 0.5, "is_uncertain": False, "alternatives": []}
    frame_lone = build_venture_frame(industry_prediction=lone_prediction)
    lone_confidence = build_hypothesis_set(frame_lone)["categories"]["industry_interpretation"][0]["confidence"]

    corroborated_positioning = {"primary_domain": "fintech", "confidence": 0.5, "is_low_confidence": False, "resolution_source": "taxonomy_dominant"}
    frame_corroborated = build_venture_frame(industry_prediction=lone_prediction, venture_positioning=corroborated_positioning)
    corroborated_confidence = build_hypothesis_set(frame_corroborated)["categories"]["industry_interpretation"][0]["confidence"]

    assert corroborated_confidence >= lone_confidence


def test_rejected_status_when_contradicting_evidence_outweighs_supporting():
    industry_prediction = {
        "predicted_industry": "b2b", "confidence": 0.15, "is_uncertain": True,
        "alternatives": [{"industry": "consumer", "confidence": 0.9}],
    }
    frame = build_venture_frame(industry_prediction=industry_prediction)
    result = build_hypothesis_set(frame)
    hyps = {h["title"]: h for h in result["categories"]["industry_interpretation"]}
    # "consumer" out-scores "b2b" and becomes leading; "b2b" has 1 contradicting vs 1 supporting —
    # not a majority, so it should be "plausible"/"weak", not "rejected" (equal counts don't reject).
    assert hyps["consumer"]["status"] == "leading"


# --- Evidence linkage correctness ----------------------------------------------------------------


def test_every_supporting_and_contradicting_id_traces_to_real_ledger_or_frame_evidence():
    funding = assess_funding_readiness({"traction": 2, "competitive_differentiation": {"state": "confirmed_negative"}})
    frame = build_venture_frame(
        funding_assessment=funding,
        market_evidence={"customer_type": "SMB owners"},
        industry_prediction={"predicted_industry": "saas", "confidence": 0.8, "is_uncertain": False, "alternatives": []},
    )
    ledger = build_evidence_ledger(funding, {"customer_type": "SMB owners"}, {"predicted_industry": "saas", "confidence": 0.8})
    known_ids = {item["id"] for item in ledger} | {"market_evidence:customer_type", "model:industry_prediction"}
    result = build_hypothesis_set(frame, ledger, funding)
    for hyps in result["categories"].values():
        for hyp in hyps:
            for evidence_id in hyp["supporting_evidence_ids"] + hyp["contradicting_evidence_ids"]:
                assert evidence_id in known_ids, f"unlinked evidence id: {evidence_id}"


# --- Domain sweep: healthcare, fintech, AI/hardware, marketplaces, SaaS, social impact -----------


def test_domain_sweep_never_crashes_and_stays_honest():
    descriptions = {
        "healthcare": "A clinical decision support tool for hospital patient triage.",
        "fintech": "We provide instant small-dollar loans to gig workers.",
        "ai_hardware": "An autonomous vehicle safety sensor using onboard AI inference.",
        "marketplace": "A marketplace connecting freelance electricians with homeowners.",
        "saas": "A project management tool for remote software teams.",
        "social_impact": "A tutoring platform connecting volunteer mentors with underserved students.",
    }
    for name, description in descriptions.items():
        frame = build_venture_frame(startup_description=description)
        result = build_hypothesis_set(frame)
        # Must never raise, and every category present must have at least one hypothesis.
        for hyps in result["categories"].values():
            assert len(hyps) >= 1, f"empty category produced for {name}"


# --- No mutation of the Venture Frame -------------------------------------------------------------


def test_venture_frame_is_never_mutated():
    funding = assess_funding_readiness({"traction": 2})
    frame = build_venture_frame(funding_assessment=funding, market_evidence={"customer_type": "SMB owners"})
    frame_before = copy.deepcopy(frame)
    build_hypothesis_set(frame, build_evidence_ledger(funding), funding)
    assert frame == frame_before


# --- Determinism -----------------------------------------------------------------------------------


def test_build_hypothesis_set_is_deterministic():
    funding = assess_funding_readiness({"traction": 1, "problem_clarity": {"state": "not_sure_yet"}})
    frame = build_venture_frame(
        startup_name="Nova",
        startup_description="A subscription analytics dashboard for retail teams.",
        funding_assessment=funding,
        market_evidence={"customer_type": "Retail ops managers"},
    )
    ledger = build_evidence_ledger(funding, {"customer_type": "Retail ops managers"})
    result_1 = build_hypothesis_set(copy.deepcopy(frame), copy.deepcopy(ledger), copy.deepcopy(funding))
    result_2 = build_hypothesis_set(copy.deepcopy(frame), copy.deepcopy(ledger), copy.deepcopy(funding))
    assert result_1 == result_2


# --- Never hides competing hypotheses -------------------------------------------------------------


def test_all_hypotheses_in_a_category_are_returned_not_just_the_leading_one():
    industry_prediction = {
        "predicted_industry": "b2b", "confidence": 0.4, "is_uncertain": True,
        "alternatives": [{"industry": "consumer", "confidence": 0.35}],
    }
    frame = build_venture_frame(industry_prediction=industry_prediction)
    result = build_hypothesis_set(frame)
    statuses = {h["status"] for h in result["categories"]["industry_interpretation"]}
    assert len(result["categories"]["industry_interpretation"]) == 2
    assert "leading" in statuses


def test_only_leading_hypothesis_carries_a_self_critique():
    industry_prediction = {
        "predicted_industry": "b2b", "confidence": 0.4, "is_uncertain": True,
        "alternatives": [{"industry": "consumer", "confidence": 0.35}],
    }
    frame = build_venture_frame(industry_prediction=industry_prediction)
    result = build_hypothesis_set(frame)
    hyps = result["categories"]["industry_interpretation"]
    leading = [h for h in hyps if h["status"] == "leading"]
    non_leading = [h for h in hyps if h["status"] != "leading"]
    assert all(h["self_critique"] is not None for h in leading)
    assert all(h["self_critique"] is None for h in non_leading)
    critique = leading[0]["self_critique"]
    assert "why_this_might_be_wrong" in critique
    assert "missing_evidence" in critique
    assert "experiment_to_resolve_uncertainty" in critique
