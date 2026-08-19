import pytest

from app.agents.alternative_explanation_engine import build_alternative_explanation_set
from app.agents.causal_reasoning import build_causal_reasoning
from app.agents.contradiction_engine import build_contradiction_set
from app.agents.decision_synthesis import build_decision_synthesis
from app.agents.evidence_ledger import build_evidence_ledger, summarize_ledger
from app.agents.hypothesis_set import build_hypothesis_set
from app.agents.strategic_opportunity import build_deterministic_strategic_opportunity
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
    with_strategic_opportunity=False,
    founder_guidance_items=None,
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
        founder_guidance_items=founder_guidance_items,
    )
    strategic_opportunity = None
    if with_strategic_opportunity:
        strategic_opportunity = build_deterministic_strategic_opportunity(
            venture_positioning or {}, None, None, business_model, competitor_analysis,
            {"premature_capabilities": [], "present_capabilities": []}, founder_guidance_items or [], funding_assessment,
            startup_description,
        )
    return {
        "decision_synthesis": decision_synthesis,
        "venture_frame": venture_frame,
        "funding_assessment": funding_assessment,
        "strategic_opportunity": strategic_opportunity,
        "founder_guidance_items": founder_guidance_items,
    }


CHAIN_KEYS = {
    "id", "title", "cause", "effect", "confidence", "evidence_ids", "assumptions",
    "intermediate_steps", "strength", "limitations", "what_breaks_this_chain", "what_strengthens_this_chain",
}


def _all_chains(result):
    chains = []
    if result["primary_chain"]:
        chains.append(result["primary_chain"])
    chains.extend(result["secondary_chains"])
    return chains


# --- empty / one-line ideas ------------------------------------------------------------------


def test_empty_idea_produces_no_crash():
    args = _pipeline()
    result = build_causal_reasoning(**args)
    assert result["causal_reasoning_version"] == "v1"
    # Even with no confirmed evidence, decision_synthesis still exists (readiness always computes),
    # so the flagship evidence-quality chain still fires.
    assert result["primary_chain"] is not None


def test_one_line_idea_with_some_evidence_produces_chains():
    args = _pipeline(startup_description="A tool for small businesses.", funding_answers={"problem_clarity": 2})
    result = build_causal_reasoning(**args)
    assert result["primary_chain"] is not None
    assert len(_all_chains(result)) >= 2  # evidence-quality chain + at least one rubric chain


def test_all_none_inputs_return_empty_structure_safely():
    result = build_causal_reasoning()
    assert result["primary_chain"] is None
    assert result["secondary_chains"] == []
    assert result["causal_graph"] == {"nodes": [], "edges": [], "has_cycle": False, "out_degree": {}}
    assert result["weakest_link"] is None


# --- determinism -----------------------------------------------------------------------------


def test_deterministic_output():
    industry_prediction = {"predicted_industry": "saas", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2, "traction": 2})
    first = build_causal_reasoning(**args)
    second = build_causal_reasoning(**args)
    assert first == second


# --- schema shape / evidence linkage ----------------------------------------------------------


def test_every_chain_has_full_schema_and_real_evidence_ids():
    industry_prediction = {"predicted_industry": "saas", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    funding_answers = {"problem_clarity": 2, "traction": {"state": "confirmed_negative"}, "competitive_differentiation": 2}
    args = _pipeline(industry_prediction=industry_prediction, funding_answers=funding_answers)
    ledger_ids = {item["id"] for item in build_evidence_ledger(args["funding_assessment"], None, industry_prediction)}
    result = build_causal_reasoning(**args)
    for chain in _all_chains(result):
        assert CHAIN_KEYS.issubset(chain.keys())
        assert chain["strength"] in ("strong", "moderate", "correlation_only", "unknown")
        assert 0.0 <= chain["confidence"] <= 1.0
        for evidence_id in chain["evidence_ids"]:
            assert evidence_id in ledger_ids


# --- no duplicated causes / effects / cycles ---------------------------------------------------


def test_no_duplicate_chain_ids():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": 2, "team_completeness": 2})
    result = build_causal_reasoning(**args)
    ids = [c["id"] for c in _all_chains(result)]
    assert len(ids) == len(set(ids))


def test_no_cycles_in_causal_graph():
    industry_prediction = {"predicted_industry": "saas", "confidence": 0.5, "is_uncertain": True, "alternatives": [{"industry": "fintech", "confidence": 0.45}]}
    args = _pipeline(industry_prediction=industry_prediction, funding_answers={"problem_clarity": 2, "traction": 2, "team_completeness": {"state": "confirmed_negative"}})
    result = build_causal_reasoning(**args)
    assert result["causal_graph"]["has_cycle"] is False


# --- confidence propagation: unresolved contradictions lower the flagship chain's confidence ---


def test_ambiguity_lowers_evidence_quality_chain_confidence():
    ambiguous = {"predicted_industry": "saas", "confidence": 0.5, "is_uncertain": True, "alternatives": [{"industry": "fintech", "confidence": 0.45}]}
    confident = {"predicted_industry": "saas", "confidence": 0.95, "is_uncertain": False, "alternatives": []}
    ambiguous_args = _pipeline(industry_prediction=ambiguous, funding_answers={"problem_clarity": 2})
    confident_args = _pipeline(industry_prediction=confident, funding_answers={"problem_clarity": 2})
    ambiguous_result = build_causal_reasoning(**ambiguous_args)
    confident_result = build_causal_reasoning(**confident_args)
    assert ambiguous_result["primary_chain"]["confidence"] <= confident_result["primary_chain"]["confidence"]


# --- correct dependency ordering: rubric chains never emitted for not_sure_yet/not_applicable --


def test_not_sure_yet_dimension_never_produces_a_rubric_chain():
    args = _pipeline(funding_answers={"traction": {"state": "not_sure_yet"}})
    result = build_causal_reasoning(**args)
    causes = {c["cause"] for c in _all_chains(result)}
    assert "Distribution & Traction" not in causes


def test_confirmed_negative_still_produces_a_rubric_chain():
    args = _pipeline(funding_answers={"traction": {"state": "confirmed_negative"}})
    result = build_causal_reasoning(**args)
    causes = {c["cause"] for c in _all_chains(result)}
    assert "Distribution & Traction" in causes


# --- weak vs strong evidence --------------------------------------------------------------------


def test_rubric_chains_are_always_strong():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}})
    result = build_causal_reasoning(**args)
    rubric_chains = [c for c in _all_chains(result) if c["effect"] == "Funding Readiness"]
    assert rubric_chains
    assert all(c["strength"] == "strong" for c in rubric_chains)


def test_competition_to_differentiation_is_correlation_only_when_present():
    venture_positioning = {"primary_domain": "saas", "confidence": 0.8, "is_low_confidence": False, "resolution_source": "taxonomy", "secondary_domains": []}
    args = _pipeline(
        venture_positioning=venture_positioning,
        competitor_analysis={"verified_competitors": [{"name": "Acme"}]},
        funding_answers={"competitive_differentiation": 2},
    )
    result = build_causal_reasoning(**args)
    comp_chain = next((c for c in _all_chains(result) if c["cause"] == "Named Competition"), None)
    assert comp_chain is not None
    assert comp_chain["strength"] == "correlation_only"


# --- regulated ventures / domain sweep -----------------------------------------------------------


@pytest.mark.parametrize(
    "domain",
    ["healthcare", "artificial intelligence", "fintech", "marketplace", "hardware", "education", "consumer", "social impact"],
)
def test_domain_sweep_never_crashes_and_never_fabricates(domain):
    industry_prediction = {"predicted_industry": domain, "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    args = _pipeline(
        startup_description=f"A venture in {domain} handling regulated data.",
        industry_prediction=industry_prediction,
        funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}},
    )
    ledger_ids = {item["id"] for item in build_evidence_ledger(args["funding_assessment"], None, industry_prediction)}
    result = build_causal_reasoning(**args)
    for chain in _all_chains(result):
        for evidence_id in chain["evidence_ids"]:
            assert evidence_id in ledger_ids


# --- weakest_link / highest_leverage_point / highest_uncertainty selection ------------------------


def test_weakest_link_is_the_minimum_confidence_chain():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}, "team_completeness": 2})
    result = build_causal_reasoning(**args)
    all_chains = _all_chains(result)
    assert result["weakest_link"]["confidence"] == min(c["confidence"] for c in all_chains)


def test_highest_leverage_point_has_nonzero_out_degree_when_graph_has_edges():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": {"state": "confirmed_negative"}})
    result = build_causal_reasoning(**args)
    leverage = result["highest_leverage_point"]
    assert leverage is not None
    assert result["causal_graph"]["out_degree"].get(leverage["cause"], 0) >= 1


def test_critical_dependencies_are_deduplicated_assumptions():
    args = _pipeline(funding_answers={"problem_clarity": 2, "traction": 2, "team_completeness": 2})
    result = build_causal_reasoning(**args)
    assert len(result["critical_dependencies"]) == len(set(result["critical_dependencies"]))
    assert result["critical_dependencies"]
