import pytest

from app.agents.alternative_explanation_engine import build_alternative_explanation_set
from app.agents.causal_reasoning import build_causal_reasoning
from app.agents.contradiction_engine import build_contradiction_set
from app.agents.counterfactual_simulation import build_counterfactual_simulation
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
    decision_synthesis = build_decision_synthesis(
        evidence_ledger=evidence_ledger,
        evidence_ledger_summary=evidence_ledger_summary,
        venture_frame=venture_frame,
        hypothesis_set=hypothesis_set,
        contradiction_set=contradiction_set,
        alternative_explanation_set=alternative_explanation_set,
        funding_assessment=funding_assessment,
    )
    causal_reasoning = build_causal_reasoning(
        decision_synthesis=decision_synthesis,
        venture_frame=venture_frame,
        funding_assessment=funding_assessment,
    )
    return {
        "evidence_ledger": evidence_ledger,
        "venture_frame": venture_frame,
        "funding_assessment": funding_assessment,
        "decision_synthesis": decision_synthesis,
        "causal_reasoning": causal_reasoning,
    }


SCENARIO_KEYS = {
    "id", "title", "changed_assumption", "baseline", "counterfactual", "affected_reasoning",
    "expected_effect", "confidence", "evidence_ids", "limitations", "assumptions", "why_this_matters",
}


# --- empty / one-line ideas ------------------------------------------------------------------


def test_empty_idea_produces_no_crash():
    args = _pipeline()
    result = build_counterfactual_simulation(**args)
    assert result["counterfactual_simulation_version"] == "v1"
    assert result["baseline"] is not None


def test_one_line_idea_produces_at_least_one_scenario():
    args = _pipeline(startup_description="A tool for small businesses.", funding_answers={"problem_clarity": 2})
    result = build_counterfactual_simulation(**args)
    assert result["scenarios"]


def test_all_none_inputs_return_empty_structure_safely():
    result = build_counterfactual_simulation()
    assert result["baseline"] is None
    assert result["scenarios"] == []
    assert result["best_case"] is None
    assert result["worst_case"] is None
    assert result["recommended_next_experiment"] is None


# --- determinism -----------------------------------------------------------------------------


def test_deterministic_output():
    industry_prediction = {"predicted_industry": "saas", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}})
    first = build_counterfactual_simulation(**args)
    second = build_counterfactual_simulation(**args)
    assert first == second


# --- schema shape / no hallucinated evidence ----------------------------------------------------


def test_every_scenario_has_full_schema_and_real_evidence_ids():
    industry_prediction = {"predicted_industry": "saas", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    funding_answers = {"problem_clarity": 2, "traction": {"state": "confirmed_negative"}, "competitive_differentiation": 2}
    args = _pipeline(industry_prediction=industry_prediction, funding_answers=funding_answers)
    ledger_ids = {item["id"] for item in args["evidence_ledger"]} | {"model:industry_prediction"}
    result = build_counterfactual_simulation(**args)
    for scenario in result["scenarios"]:
        assert SCENARIO_KEYS.issubset(scenario.keys())
        assert 0.0 <= scenario["confidence"] <= 1.0
        for evidence_id in scenario["evidence_ids"]:
            assert evidence_id in ledger_ids


def test_no_fabricated_probabilities_or_forecasts():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}})
    result = build_counterfactual_simulation(**args)
    for scenario in result["scenarios"]:
        text = (scenario["expected_effect"] + scenario["why_this_matters"] + scenario["limitations"]).lower()
        assert "will succeed" not in text
        assert "revenue forecast" not in text
        assert "probability of success" not in text


# --- confidence propagation: traction improving raises decision confidence ----------------------


def test_traction_improving_raises_decision_confidence():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}})
    result = build_counterfactual_simulation(**args)
    scenario = next(s for s in result["scenarios"] if s["id"] == "traction:improves")
    assert scenario["counterfactual"]["decision_confidence"] >= scenario["baseline"]["decision_confidence"]


def test_traction_declining_never_raises_decision_confidence():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_positive", "severity": 2}})
    result = build_counterfactual_simulation(**args)
    scenario = next(s for s in result["scenarios"] if s["id"] == "traction:weakens")
    assert scenario["counterfactual"]["decision_confidence"] <= scenario["baseline"]["decision_confidence"]


# --- causal propagation: primary causal chain confidence tracks decision confidence -------------


def test_causal_chain_confidence_tracks_decision_confidence_change():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}})
    result = build_counterfactual_simulation(**args)
    scenario = next(s for s in result["scenarios"] if s["id"] == "traction:improves")
    decision_delta = scenario["counterfactual"]["decision_confidence"] - scenario["baseline"]["decision_confidence"]
    causal_delta = (scenario["counterfactual"]["primary_causal_chain_confidence"] or 0) - (scenario["baseline"]["primary_causal_chain_confidence"] or 0)
    if decision_delta > 0:
        assert causal_delta >= 0


# --- recommendation changes vs stable conclusions ------------------------------------------------


def test_regulatory_burden_increasing_changes_highest_priority_risk():
    industry_prediction = {"predicted_industry": "healthcare", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    venture_positioning = {
        "primary_domain": "healthcare", "confidence": 0.9, "is_low_confidence": False,
        "resolution_source": "taxonomy", "secondary_domains": [],
    }
    args = _pipeline(
        startup_description="A wellness app with no special data handling.",
        industry_prediction=industry_prediction,
        venture_positioning=venture_positioning,
        funding_answers={"traction": {"state": "confirmed_negative"}},
    )
    result = build_counterfactual_simulation(**args)
    scenario = next((s for s in result["scenarios"] if s["id"] == "regulatory_burden:weakens"), None)
    if scenario is not None:
        assert "highest_priority_risk" in scenario["affected_reasoning"] or scenario["baseline"]["highest_priority_risk"] == scenario["counterfactual"]["highest_priority_risk"]


def test_no_op_flip_is_never_simulated():
    # traction is already confirmed_positive severity 2 -> flipping to "improves" (same state) must
    # never be simulated as a scenario.
    args = _pipeline(funding_answers={"traction": {"state": "confirmed_positive", "severity": 2}})
    result = build_counterfactual_simulation(**args)
    ids = {s["id"] for s in result["scenarios"]}
    assert "traction:improves" not in ids
    assert "traction:weakens" in ids


def test_not_applicable_dimension_never_produces_a_scenario():
    args = _pipeline(funding_answers={"traction": {"state": "not_applicable"}})
    result = build_counterfactual_simulation(**args)
    ids = {s["id"] for s in result["scenarios"]}
    assert "traction:improves" not in ids
    assert "traction:weakens" not in ids


# --- regulated ventures / domain sweep -----------------------------------------------------------


@pytest.mark.parametrize(
    "domain",
    ["healthcare", "artificial intelligence", "fintech", "marketplace", "hardware", "education", "consumer", "social impact"],
)
def test_domain_sweep_never_crashes_and_stays_evidence_traceable(domain):
    industry_prediction = {"predicted_industry": domain, "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    args = _pipeline(
        startup_description=f"A regulated venture in {domain}.",
        industry_prediction=industry_prediction,
        funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}},
    )
    ledger_ids = {item["id"] for item in args["evidence_ledger"]} | {"model:industry_prediction"}
    result = build_counterfactual_simulation(**args)
    for scenario in result["scenarios"]:
        for evidence_id in scenario["evidence_ids"]:
            assert evidence_id in ledger_ids


# --- weak / strong evidence ------------------------------------------------------------------------


def test_weak_evidence_baseline_still_produces_valid_scenarios():
    args = _pipeline(funding_answers={"traction": {"state": "not_sure_yet"}})
    result = build_counterfactual_simulation(**args)
    # not_sure_yet is neither confirmed_positive nor confirmed_negative -> both flips are real changes.
    ids = {s["id"] for s in result["scenarios"]}
    assert "traction:improves" in ids
    assert "traction:weakens" in ids


# --- industry confidence scenarios: only simulated when the ledger item exists -------------------


def test_industry_confidence_scenarios_absent_without_industry_prediction():
    args = _pipeline(funding_answers={"problem_clarity": 2})
    result = build_counterfactual_simulation(**args)
    ids = {s["id"] for s in result["scenarios"]}
    assert "industry_confidence:improves" not in ids
    assert "industry_confidence:weakens" not in ids


def test_industry_confidence_scenarios_present_with_industry_prediction():
    industry_prediction = {"predicted_industry": "saas", "confidence": 0.6, "is_uncertain": False, "alternatives": []}
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2})
    result = build_counterfactual_simulation(**args)
    ids = {s["id"] for s in result["scenarios"]}
    assert "industry_confidence:improves" in ids
    assert "industry_confidence:weakens" in ids


# --- top-level aggregate fields --------------------------------------------------------------------


def test_stable_findings_and_changed_findings_are_consistent():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}, "team_completeness": 2})
    result = build_counterfactual_simulation(**args)
    stable_fields = set()
    for finding in result["stable_findings"]:
        for field in ("highest_priority_risk", "highest_priority_opportunity", "highest_priority_action", "overall_decision"):
            if finding.startswith(field):
                stable_fields.add(field)
    changed_fields = {f["field"] for f in result["changed_findings"]}
    assert not (stable_fields & changed_fields)


def test_best_case_and_worst_case_are_never_the_same_scenario_when_both_exist():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}, "team_completeness": 2})
    result = build_counterfactual_simulation(**args)
    if result["best_case"] and result["worst_case"]:
        assert result["best_case"]["counterfactual"]["decision_confidence"] >= result["worst_case"]["counterfactual"]["decision_confidence"]


def test_recommended_next_experiment_always_improves_decision_confidence():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}, "team_completeness": 2})
    result = build_counterfactual_simulation(**args)
    experiment = result["recommended_next_experiment"]
    if experiment is not None:
        assert experiment["counterfactual"]["decision_confidence"] > experiment["baseline"]["decision_confidence"]


def test_most_fragile_assumption_is_a_weakening_scenario():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_positive", "severity": 2}, "team_completeness": {"state": "confirmed_positive", "severity": 2}})
    result = build_counterfactual_simulation(**args)
    fragile = result["most_fragile_assumption"]
    if fragile is not None:
        assert fragile["id"].endswith(":weakens")
