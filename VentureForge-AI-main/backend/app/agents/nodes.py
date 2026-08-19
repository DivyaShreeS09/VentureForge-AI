"""Orchestrator node functions. Each is a plain, independently-testable function: takes the
current state, returns the keys it updates (LangGraph merges these into state). No node calls
another node directly — routing is decided by orchestrator.py alone (deterministic, no loops).
"""

from __future__ import annotations

import logging

from app.agents.business_model_agent import generate_business_model
from app.agents.competitor_agent import generate_competitor_analysis
from app.agents.competitor_reviewer import suggest_competitor_possibilities_safely
from app.agents.customer_persona_agent import generate_customer_persona
from app.agents.idea_expansion import build_deterministic_idea_expansion
from app.agents.idea_expansion_reviewer import build_idea_expansion_context, generate_idea_expansion_safely
from app.agents.market_agent import generate_market_analysis
from app.agents.mentor_reviewer import build_mentor_context, review_mentor_safely
from app.agents.mentor_synthesis import build_deterministic_mentor
from app.agents.positioning_reviewer import review_positioning_safely
from app.agents.strategic_opportunity import build_deterministic_strategic_opportunity
from app.agents.strategic_opportunity_reviewer import (
    build_strategic_opportunity_context,
    generate_strategic_opportunity_safely,
)
from app.agents import student3
from app.agents.state import OrchestratorState, TraceStep
from app.agents.venture_positioning import build_model_category, resolve_venture_positioning
from app.ml.funding_readiness import assess_funding_readiness
from app.ml.positioning_taxonomy import score_taxonomy, taxonomy_is_ambiguous
from app.ml.predictor import IndustryClassifierUnavailable, predict_industry
from app.ml.revenue_scenario import estimate_revenue_scenario
from app.ml.success_predictor import SuccessPredictorUnavailable, predict_success

logger = logging.getLogger(__name__)

MIN_DESCRIPTION_LENGTH = 10


def _trace(node: str, status: str, detail: str | None = None) -> TraceStep:
    return {"node": node, "status": status, "detail": detail}


def input_validation_node(state: OrchestratorState) -> dict:
    errors: list[str] = []
    name = (state.get("startup_name") or "").strip()
    description = (state.get("startup_description") or "").strip()

    if not name:
        errors.append("startup_name is required")
    if len(description) < MIN_DESCRIPTION_LENGTH:
        errors.append(f"startup_description must be at least {MIN_DESCRIPTION_LENGTH} characters")

    valid = not errors
    return {
        "validation": {"valid": valid, "errors": errors},
        "trace": [_trace("input_validation", "ok" if valid else "error", "; ".join(errors) or None)],
    }


def industry_classification_node(state: OrchestratorState) -> dict:
    try:
        result = predict_industry(state.get("startup_name", ""), state.get("startup_description", ""))
        return {
            "industry_prediction": result,
            "trace": [_trace("industry_classification", "ok")],
        }
    except IndustryClassifierUnavailable as exc:
        logger.warning("Industry classifier unavailable: %s", exc)
        return {
            "industry_prediction": None,
            "trace": [_trace("industry_classification", "error", str(exc))],
        }


def funding_readiness_node(state: OrchestratorState) -> dict:
    assessment = assess_funding_readiness(state.get("funding_answers") or {})
    return {
        "funding_assessment": assessment,
        "trace": [_trace("funding_readiness", "ok")],
    }


def success_prediction_node(state: OrchestratorState) -> dict:
    metrics = state.get("company_metrics") or {}
    industry_prediction = state.get("industry_prediction")
    try:
        result = predict_success(
            total_funding_usd=metrics.get("total_funding_usd"),
            funding_rounds=metrics.get("funding_rounds"),
            founded_year=metrics.get("founded_year"),
            country_code=metrics.get("country_code"),
            industry=(industry_prediction or {}).get("predicted_industry"),
        )
        return {
            "success_prediction": result,
            "trace": [_trace("success_prediction", "ok")],
        }
    except SuccessPredictorUnavailable as exc:
        logger.warning("Success predictor unavailable: %s", exc)
        return {
            "success_prediction": None,
            "trace": [_trace("success_prediction", "error", str(exc))],
        }


def revenue_estimate_node(state: OrchestratorState) -> dict:
    assumptions = state.get("revenue_assumptions") or {}
    venture_positioning = state.get("venture_positioning") or {}
    model_category = state.get("model_category") or {}
    result = estimate_revenue_scenario(
        price_per_customer_usd=assumptions.get("price_per_customer_usd"),
        initial_customers=assumptions.get("initial_customers"),
        monthly_growth_rate_pct=assumptions.get("monthly_growth_rate_pct"),
        gross_margin_pct=assumptions.get("gross_margin_pct"),
        primary_domain=venture_positioning.get("primary_domain"),
        model_category_label=model_category.get("label"),
    )
    return {
        "revenue_estimate": result,
        "trace": [_trace("revenue_estimate", "ok")],
    }


def market_analysis_node(state: OrchestratorState) -> dict:
    result = generate_market_analysis(
        industry_prediction=state.get("industry_prediction"),
        funding_assessment=state.get("funding_assessment") or {},
        market_evidence=state.get("market_evidence") or {},
    )
    return {
        "market_intelligence": result,
        "trace": [_trace("market_analysis", "ok")],
    }


def competitor_analysis_node(state: OrchestratorState) -> dict:
    market_evidence = state.get("market_evidence") or {}
    known_competitors = market_evidence.get("known_competitors") or []
    model_category = state.get("model_category") or {}
    venture_positioning = state.get("venture_positioning") or {}

    # Only worth asking Gemini for category-level possibilities when the founder didn't already
    # name real competitors themselves — never invoked otherwise, keeping this deterministic and
    # network-free in the common case.
    unverified_possibilities: list[dict] = []
    if not known_competitors:
        unverified_possibilities = suggest_competitor_possibilities_safely(
            state.get("startup_description", ""),
            model_category.get("label"),
            venture_positioning.get("primary_domain"),
        )

    result = generate_competitor_analysis(
        known_competitors=known_competitors,
        industry_prediction=state.get("industry_prediction"),
        unverified_possibilities=unverified_possibilities,
    )
    return {
        "competitor_analysis": result,
        "trace": [_trace("competitor_analysis", "ok")],
    }


def customer_persona_node(state: OrchestratorState) -> dict:
    result = generate_customer_persona(
        market_evidence=state.get("market_evidence") or {},
        industry_prediction=state.get("industry_prediction"),
    )
    return {
        "customer_personas": result,
        "trace": [_trace("customer_persona", "ok")],
    }


def business_model_node(state: OrchestratorState) -> dict:
    result = generate_business_model(
        startup_description=state.get("startup_description", ""),
        market_evidence=state.get("market_evidence") or {},
        revenue_estimate=state.get("revenue_estimate") or {},
        funding_assessment=state.get("funding_assessment") or {},
    )
    return {
        "business_model": result,
        "trace": [_trace("business_model", "ok")],
    }


def venture_positioning_node(state: OrchestratorState) -> dict:
    """Resolve the founder-facing `venture_positioning` (Phase 0.5) — see
    app.agents.venture_positioning. Gemini is only invoked when the deterministic taxonomy
    signal is ambiguous or the raw model category is itself uncertain; otherwise a clean,
    confident taxonomy match never touches the network.
    """
    industry_prediction = state.get("industry_prediction")
    description = state.get("startup_description", "")
    model_category = build_model_category(industry_prediction)
    taxonomy_result = score_taxonomy(description)

    needs_review = taxonomy_is_ambiguous(taxonomy_result["candidates"]) or (model_category or {}).get(
        "is_uncertain", True
    )
    gemini_recommendation = None
    if needs_review:
        candidate_domains = [c["domain"] for c in taxonomy_result["candidates"][:5]]
        gemini_recommendation = review_positioning_safely(description, model_category, candidate_domains)

    resolution = resolve_venture_positioning(taxonomy_result, model_category, gemini_recommendation)

    return {
        "model_category": model_category,
        "taxonomy_candidates": taxonomy_result["candidates"],
        "gemini_structured_recommendation": (
            gemini_recommendation.model_dump() if gemini_recommendation is not None else None
        ),
        "gemini_rationale": gemini_recommendation.rationale if gemini_recommendation is not None else None,
        "venture_positioning": resolution["venture_positioning"],
        "positioning_correction_rationale": resolution["correction_rationale"],
        "trace": [_trace("venture_positioning", "ok")],
    }


def mentor_synthesis_node(state: OrchestratorState) -> dict:
    """Full Mentor Orchestration phase: reconciles the Judge Agent's output plus every
    business-intelligence agent's output into one coherent MentorInterpretation (see
    app.agents.mentor_synthesis). Always runs the deterministic synthesis first (the complete
    fallback — see that module's docstring), then optionally lets Gemini rephrase a narrow,
    safety-checked subset of it (app.agents.mentor_reviewer) — never the other way around.
    """
    judge_summary = state.get("judge_summary")
    if judge_summary is None:
        # The judge node already failed upstream (see orchestrator._judge_node) — nothing to
        # synthesize a mentor result from.
        return {"mentor_interpretation": None, "trace": [_trace("mentor_synthesis", "skipped", "judge_summary unavailable")]}

    startup_name = state.get("startup_name", "")
    startup_description = state.get("startup_description", "")
    baseline = build_deterministic_mentor(
        startup_name=startup_name,
        startup_description=startup_description,
        judge_summary=judge_summary,
        funding_assessment=state.get("funding_assessment") or {},
        success_prediction=state.get("success_prediction"),
        revenue_estimate=state.get("revenue_estimate"),
        market_intelligence=state.get("market_intelligence"),
        competitor_analysis=state.get("competitor_analysis"),
        customer_personas=state.get("customer_personas"),
        business_model=state.get("business_model"),
        market_evidence=state.get("market_evidence") or {},
    )

    context = build_mentor_context(startup_name, startup_description, baseline)
    mentor_result = review_mentor_safely(context, baseline, startup_name, startup_description)
    return {"mentor_interpretation": mentor_result, "trace": [_trace("mentor_synthesis", "ok")]}


def idea_expansion_node(state: OrchestratorState) -> dict:
    """Idea Expansion (Phase 2): always runs the deterministic baseline first (see
    app.agents.idea_expansion — the complete fallback), then optionally lets Gemini append a
    narrow, safety-checked set of additional, clearly-tiered possibilities on top (see
    app.agents.idea_expansion_reviewer) — never the other way around, and never replacing a
    deterministic item.
    """
    mentor = state.get("mentor_interpretation")
    if mentor is None:
        return {"idea_expansion": None, "trace": [_trace("idea_expansion", "skipped", "mentor_interpretation unavailable")]}

    venture_positioning = (state.get("judge_summary") or {}).get("venture_positioning") or {}
    feature_gap = mentor.get("feature_gap_analysis") or {}
    mvp_recommendation = mentor.get("mvp_recommendation") or {}
    funding_level = (mentor.get("mentor_verdict") or {}).get("readiness_level", "early_stage")
    startup_name = state.get("startup_name", "")
    startup_description = state.get("startup_description", "")

    baseline = build_deterministic_idea_expansion(
        venture_positioning, feature_gap, mvp_recommendation, state.get("market_evidence") or {}
    )
    context = build_idea_expansion_context(
        startup_name, startup_description, venture_positioning, feature_gap, mvp_recommendation, funding_level
    )
    result = generate_idea_expansion_safely(context, baseline)
    return {"idea_expansion": result, "trace": [_trace("idea_expansion", "ok")]}


def strategic_opportunity_node(state: OrchestratorState) -> dict:
    """Strategic Opportunity Discovery (Phase 3): always runs the deterministic baseline first
    (see app.agents.strategic_opportunity — the complete fallback, including the fully
    deterministic `primary_opportunity`), then optionally lets Gemini append a narrow,
    safety-checked set of additional adjacent-market/future-expansion reasoning and strategic
    risks on top (see app.agents.strategic_opportunity_reviewer) — never the other way around, and
    never replacing a deterministic item or touching `primary_opportunity`.
    """
    mentor = state.get("mentor_interpretation")
    if mentor is None:
        return {"strategic_opportunity": None, "trace": [_trace("strategic_opportunity", "skipped", "mentor_interpretation unavailable")]}

    judge_summary = state.get("judge_summary") or {}
    venture_positioning = judge_summary.get("venture_positioning") or {}
    feature_gap = mentor.get("feature_gap_analysis") or {}
    founder_guidance_items = mentor.get("founder_guidance_items") or []
    funding_assessment = state.get("funding_assessment") or {}
    funding_level = (mentor.get("mentor_verdict") or {}).get("readiness_level", "early_stage")
    market_intelligence = state.get("market_intelligence")
    customer_personas = state.get("customer_personas")
    business_model = state.get("business_model")
    competitor_analysis = state.get("competitor_analysis")
    startup_name = state.get("startup_name", "")
    startup_description = state.get("startup_description", "")

    baseline = build_deterministic_strategic_opportunity(
        venture_positioning, market_intelligence, customer_personas, business_model,
        competitor_analysis, feature_gap, founder_guidance_items, funding_assessment,
        startup_description=startup_description,
    )
    context = build_strategic_opportunity_context(
        startup_name, startup_description, venture_positioning, market_intelligence,
        business_model, competitor_analysis, feature_gap, funding_level,
    )
    result = generate_strategic_opportunity_safely(context, baseline)
    return {"strategic_opportunity": result, "trace": [_trace("strategic_opportunity", "ok")]}


def evidence_confidence_check_node(state: OrchestratorState) -> dict:
    notes: list[str] = []
    low_confidence = False

    prediction = state.get("industry_prediction")
    if prediction is None:
        notes.append("Industry classification unavailable — treat industry as unknown.")
        low_confidence = True
    elif prediction.get("is_uncertain"):
        low_confidence = True
        notes.extend(prediction.get("uncertainty_reasons", []))
        notes.append(
            f"Top alternative(s) should be considered alongside '{prediction['predicted_industry']}'."
        )

    assessment = state.get("funding_assessment") or {}
    missing = assessment.get("missing_evidence", [])
    if missing:
        notes.append(f"Funding readiness score is penalized by {len(missing)} missing evidence field(s).")

    return {
        "evidence_check": {"low_confidence": low_confidence, "notes": notes},
        "trace": [_trace("evidence_confidence_check", "ok")],
    }


# Phase 5 (Student 3): deterministic growth/strategy planning nodes — see app.agents.student3.
# Additive only; none of these touch industry_prediction, funding_assessment, judge_summary,
# mentor_interpretation, idea_expansion, or strategic_opportunity. Node ids are deliberately
# distinct from the OrchestratorState keys they populate, matching the existing convention (see
# "predict_success" vs `success_prediction` above).

def segment_customers_node(state: OrchestratorState) -> dict:
    segment = student3.customer_segment(
        state.get("industry_prediction"), state.get("funding_assessment") or {}, customer_rfm=state.get("customer_rfm")
    )
    return {"customer_segment": segment, "trace": [_trace("customer_segmentation", "ok", segment["method"])]}


def rank_actions_node(state: OrchestratorState) -> dict:
    actions = student3.ranked_actions(
        state.get("funding_assessment") or {}, state.get("industry_prediction"), state.get("customer_segment") or {}
    )
    return {"ranked_actions": actions, "trace": [_trace("recommendation_ranking", "ok", f"{len(actions)} action(s)")]}


def surface_innovation_node(state: OrchestratorState) -> dict:
    output = student3.innovation(state.get("industry_prediction"), state.get("funding_assessment") or {})
    return {"innovation_opportunities": output, "trace": [_trace("innovation", "ok")]}


def assess_risks_node(state: OrchestratorState) -> dict:
    output = student3.risks(state.get("funding_assessment") or {}, state.get("industry_prediction"))
    return {"risk_assessment": output, "trace": [_trace("risk_assessment", "ok")]}


def plan_growth_strategy_node(state: OrchestratorState) -> dict:
    output = student3.growth_strategy(
        state.get("customer_segment") or {}, state.get("ranked_actions") or [], state.get("industry_prediction")
    )
    return {"growth_strategy": output, "trace": [_trace("growth_strategy", "ok")]}


def build_pitch_deck_node(state: OrchestratorState) -> dict:
    output = student3.pitch_deck(
        state.get("startup_name", ""),
        state.get("startup_description", ""),
        state.get("industry_prediction"),
        state.get("funding_assessment") or {},
        state.get("customer_segment") or {},
        state.get("ranked_actions") or [],
    )
    return {"pitch_deck": output, "trace": [_trace("pitch_deck", "ok")]}
