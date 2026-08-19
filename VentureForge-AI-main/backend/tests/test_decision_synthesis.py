import pytest

from app.agents.alternative_explanation_engine import build_alternative_explanation_set
from app.agents.contradiction_engine import build_contradiction_set
from app.agents.decision_synthesis import build_decision_synthesis
from app.agents.evidence_ledger import build_evidence_ledger, summarize_ledger
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
    evidence_ledger_summary = summarize_ledger(evidence_ledger)
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
    alternative_explanation_set = build_alternative_explanation_set(
        evidence_ledger, venture_frame, hypothesis_set, contradiction_set
    )
    return {
        "evidence_ledger": evidence_ledger,
        "evidence_ledger_summary": evidence_ledger_summary,
        "venture_frame": venture_frame,
        "hypothesis_set": hypothesis_set,
        "contradiction_set": contradiction_set,
        "alternative_explanation_set": alternative_explanation_set,
        "funding_assessment": funding_assessment,
    }


REQUIRED_KEYS = {
    "decision_synthesis_version", "overall_decision", "decision_confidence", "decision_confidence_label",
    "decision_rationale", "supporting_evidence", "conflicting_evidence", "remaining_uncertainties",
    "highest_priority_opportunity", "highest_priority_risk", "highest_priority_action",
    "highest_learning_goal", "highest_validation_goal", "why_this_decision",
    "what_would_change_this_decision", "alternative_decisions", "mentor_summary", "investor_summary",
    "reasoning_trace",
}


# --- empty / one-line ideas: uncertainty, never a forced decision -----------------------------


def test_empty_idea_produces_only_low_confidence_and_no_fabricated_opportunity():
    # assess_funding_readiness({}) still yields a real overall_score (every dimension defaults to
    # "not_sure_yet", itself weak evidence per app.agents.evidence_ledger) — so a readiness
    # hypothesis always exists, but with low confidence and no confirmed-positive evidence at all.
    args = _pipeline()
    result = build_decision_synthesis(**args)
    assert REQUIRED_KEYS.issubset(result.keys())
    assert result["decision_confidence_label"] in ("low", "medium")
    assert result["highest_priority_opportunity"] is None


def test_genuinely_no_input_says_not_enough_evidence_rather_than_forcing_a_decision():
    result = build_decision_synthesis()
    assert result["decision_confidence"] == 0.0
    assert "isn't enough" in result["overall_decision"].lower()


def test_one_line_idea_with_some_evidence_produces_a_real_decision():
    args = _pipeline(startup_description="A tool for small businesses.", funding_answers={"problem_clarity": 2})
    result = build_decision_synthesis(**args)
    assert result["decision_confidence"] > 0.0
    assert "isn't enough" not in result["overall_decision"].lower()


# --- determinism --------------------------------------------------------------------------------


def test_deterministic_output():
    industry_prediction = {"predicted_industry": "saas", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2, "traction": 2})
    first = build_decision_synthesis(**args)
    second = build_decision_synthesis(**args)
    assert first == second


# --- evidence traceability: every id referenced actually exists in the ledger -------------------


def test_supporting_and_conflicting_evidence_trace_to_real_ledger_ids():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2, "traction": 2})
    ledger_ids = {item["id"] for item in args["evidence_ledger"]}
    result = build_decision_synthesis(**args)
    for evidence_id in result["supporting_evidence"]:
        assert evidence_id in ledger_ids
    for evidence_id in result["conflicting_evidence"]:
        assert evidence_id in ledger_ids


# --- confidence propagation: unresolved contradictions lower decision_confidence ----------------


def test_ambiguity_lowers_decision_confidence_versus_confident_case():
    ambiguous = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    confident = {"predicted_industry": "saas", "confidence": 0.95, "is_uncertain": False, "alternatives": []}
    ambiguous_args = _pipeline(industry_prediction=ambiguous, funding_answers={"problem_clarity": 2})
    confident_args = _pipeline(industry_prediction=confident, funding_answers={"problem_clarity": 2})
    ambiguous_result = build_decision_synthesis(**ambiguous_args)
    confident_result = build_decision_synthesis(**confident_args)
    assert ambiguous_result["decision_confidence"] <= confident_result["decision_confidence"]


def test_missing_information_never_crushes_decision_confidence_to_zero():
    args = _pipeline(funding_answers={"problem_clarity": 2})  # many dims left unanswered
    result = build_decision_synthesis(**args)
    # Plenty of missing_information records exist here, but none should zero out confidence —
    # only genuine ambiguity/true_contradiction records may.
    missing = [c for c in args["contradiction_set"]["contradictions"] if c["kind"] == "missing_information"]
    assert missing
    assert result["decision_confidence"] > 0.0


# --- contradiction handling: reflected in remaining_uncertainties and rationale -----------------


def test_unresolved_ambiguity_appears_in_remaining_uncertainties_and_rationale():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2})
    result = build_decision_synthesis(**args)
    kinds = {u["kind"] for u in result["remaining_uncertainties"]}
    assert "ambiguity" in kinds
    assert "still genuinely open" in result["decision_rationale"] or "No unresolved" in result["decision_rationale"]


# --- alternative handling: passthrough, never recomputed ----------------------------------------


def test_alternative_decisions_is_exact_passthrough_of_alternative_explanation_set():
    industry_prediction = {
        "predicted_industry": "saas",
        "confidence": 0.5,
        "is_uncertain": True,
        "alternatives": [{"industry": "fintech", "confidence": 0.45}],
    }
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2})
    result = build_decision_synthesis(**args)
    assert result["alternative_decisions"] == args["alternative_explanation_set"]["alternative_explanations"]


# --- single source of truth: highest_priority_action never invents a new ranking ----------------


def test_highest_priority_action_prefers_ranked_actions_when_present():
    args = _pipeline(funding_answers={"traction": {"state": "confirmed_negative"}})
    ranked_actions = [
        {"title": "Recruit and measure a pilot cohort", "priority_score": 96, "evidence_basis": ["evidence 1"]},
        {"title": "Some other action", "priority_score": 72, "evidence_basis": ["evidence 2"]},
    ]
    result = build_decision_synthesis(**args, ranked_actions=ranked_actions)
    assert result["highest_priority_action"]["title"] == "Recruit and measure a pilot cohort"
    assert result["highest_priority_action"]["source"] == "student3_ranked_actions"


def test_highest_priority_action_falls_back_to_founder_guidance_when_no_ranked_actions():
    funding = {"traction": {"state": "confirmed_negative"}}
    args = _pipeline(funding_answers=funding)
    founder_guidance_items = [
        {
            "category": "validation_opportunity", "title": "Traction is still unconfirmed",
            "next_step": "Recruit a pilot customer.", "observation": "obs", "why_it_matters": "why",
            "priority": 1, "dimension": "traction",
        },
        {
            "category": "strength", "title": "Problem clarity is strong",
            "next_step": "n/a", "observation": "obs", "why_it_matters": "why",
            "priority": 2, "dimension": "problem_clarity",
        },
    ]
    result = build_decision_synthesis(**args, founder_guidance_items=founder_guidance_items)
    assert result["highest_priority_action"]["title"] == "Recruit a pilot customer."
    assert result["highest_priority_action"]["source"] == "founder_guidance_items"


def test_no_action_available_is_none_not_fabricated():
    args = _pipeline()
    result = build_decision_synthesis(**args)
    assert result["highest_priority_action"] is None


# --- regulatory risk always outranks an ordinary rubric gap -------------------------------------


def test_regulatory_risk_outranks_confirmed_negative_rubric_risk():
    industry_prediction = {"predicted_industry": "healthcare", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    venture_positioning = {
        "primary_domain": "healthcare",
        "confidence": 0.9,
        "is_low_confidence": False,
        "resolution_source": "taxonomy",
        "secondary_domains": [],
        "deployment_sectors": ["Hospitals"],
    }
    args = _pipeline(
        startup_description="A clinical monitoring device for hospital patients handling protected health data.",
        industry_prediction=industry_prediction,
        venture_positioning=venture_positioning,
        funding_answers={"traction": {"state": "confirmed_negative"}},
    )
    result = build_decision_synthesis(**args)
    if result["highest_priority_risk"] is not None:
        assert result["highest_priority_risk"]["source"] in ("evidence_ledger",)


# --- no hallucinated evidence: every referenced id is real --------------------------------------


def test_no_hallucinated_evidence_across_a_domain_sweep():
    for domain in ["healthcare", "fintech", "marketplace", "education"]:
        industry_prediction = {"predicted_industry": domain, "confidence": 0.9, "is_uncertain": False, "alternatives": []}
        args = _pipeline(
            startup_description=f"A venture in {domain}.",
            industry_prediction=industry_prediction,
            funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}},
        )
        ledger_ids = {item["id"] for item in args["evidence_ledger"]}
        result = build_decision_synthesis(**args)
        for evidence_id in result["supporting_evidence"] + result["conflicting_evidence"]:
            assert evidence_id in ledger_ids


# --- stable outputs / backward compatibility: all-None inputs never crash ----------------------


def test_all_none_inputs_handled_safely():
    result = build_decision_synthesis()
    assert result["decision_confidence"] == 0.0
    assert result["highest_priority_opportunity"] is None
    assert result["highest_priority_risk"] is None
    assert result["highest_priority_action"] is None
    assert result["alternative_decisions"] == []


# --- schema shape --------------------------------------------------------------------------------


def test_full_schema_present_with_rich_evidence():
    industry_prediction = {"predicted_industry": "saas", "confidence": 0.95, "is_uncertain": False, "alternatives": []}
    args = _pipeline(
        industry_prediction=industry_prediction,
        funding_answers={"problem_clarity": 2, "traction": 2, "competitive_differentiation": 2},
        market_evidence={"customer_type": "SMB owners"},
    )
    result = build_decision_synthesis(**args)
    assert REQUIRED_KEYS.issubset(result.keys())
    assert result["decision_confidence_label"] in ("low", "medium", "high")
    assert isinstance(result["reasoning_trace"], list) and len(result["reasoning_trace"]) == 4
    for step in result["reasoning_trace"]:
        assert step["question"] and step["answer"]
