"""Business logic for creating startups and running/persisting their analysis pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.idea_expansion import build_deterministic_idea_expansion
from app.agents.idea_expansion_reviewer import build_idea_expansion_context, generate_idea_expansion_safely
from app.agents.mentor_reviewer import build_mentor_context, review_mentor_safely
from app.agents.mentor_synthesis import build_deterministic_mentor
from app.agents.orchestrator import run_pipeline
from app.agents.strategic_opportunity import build_deterministic_strategic_opportunity
from app.agents.strategic_opportunity_reviewer import (
    build_strategic_opportunity_context,
    generate_strategic_opportunity_safely,
)
from app.agents.state import OrchestratorState
from app.agents.venture_positioning import build_model_category, resolve_venture_positioning
from app.ml.positioning_taxonomy import TAXONOMY_VERSION, score_taxonomy
from app.ml.revenue_scenario import estimate_revenue_scenario
from app.models.analysis import Analysis
from app.models.startup import Startup
from app.schemas.startup import StartupCreateRequest
from app.schemas.student3 import Student3Outputs


def _regenerate_mentor_interpretation(analysis: Analysis, startup: Startup | None) -> dict | None:
    """Rebuild `mentor_interpretation` from the analysis's current, just-updated fields — called
    at the end of both `apply_industry_correction` and `apply_revenue_assumptions_update` so
    neither correction leaves a stale Mentor Interpretation behind (it previously only updated
    `judge_summary`/`revenue_estimate` and left `mentor_interpretation` untouched).

    Reuses whatever `judge_summary`, `funding_assessment`, `success_prediction`, `revenue_estimate`,
    `market_intelligence`, `competitor_analysis`, `customer_personas`, and `business_model` are
    already stored on `analysis` — this never re-runs industry classification, success prediction,
    or any other trained-model inference; it only re-synthesizes the mentor narrative from
    data that's already been computed (deterministically, plus an optional Gemini rephrasing pass,
    exactly like a fresh analysis run — see app.agents.mentor_reviewer.review_mentor_safely).

    Returns None if there is no `judge_summary` to synthesize from yet (should not happen for a
    completed analysis, but mirrors `mentor_synthesis_node`'s own guard for a failed run).
    """
    judge_summary = analysis.judge_summary
    if judge_summary is None:
        return None

    startup_name = startup.name if startup is not None else ""
    startup_description = startup.description if startup is not None else ""
    market_evidence = (startup.market_evidence if startup is not None else None) or {}

    baseline = build_deterministic_mentor(
        startup_name=startup_name,
        startup_description=startup_description,
        judge_summary=judge_summary,
        funding_assessment=analysis.funding_assessment or {},
        success_prediction=analysis.success_prediction,
        revenue_estimate=analysis.revenue_estimate,
        market_intelligence=analysis.market_intelligence,
        competitor_analysis=analysis.competitor_analysis,
        customer_personas=analysis.customer_personas,
        business_model=analysis.business_model,
        market_evidence=market_evidence,
    )
    context = build_mentor_context(startup_name, startup_description, baseline)
    return review_mentor_safely(context, baseline, startup_name, startup_description)


def _regenerate_idea_expansion(mentor_interpretation: dict | None, judge_summary: dict | None, startup: Startup | None) -> dict | None:
    """Rebuild `idea_expansion` from a just-regenerated `mentor_interpretation` — called after
    `_regenerate_mentor_interpretation` in both correction helpers below so a positioning/revenue
    correction never leaves a stale Idea Expansion (segments/adjacent industries/pivots derived
    from the now-outdated venture_positioning) behind.

    Returns None if there is no mentor_interpretation to derive from yet.
    """
    if mentor_interpretation is None:
        return None

    startup_name = startup.name if startup is not None else ""
    startup_description = startup.description if startup is not None else ""
    venture_positioning = (judge_summary or {}).get("venture_positioning") or {}
    feature_gap = mentor_interpretation.get("feature_gap_analysis") or {}
    mvp_recommendation = mentor_interpretation.get("mvp_recommendation") or {}
    funding_level = (mentor_interpretation.get("mentor_verdict") or {}).get("readiness_level", "early_stage")

    baseline = build_deterministic_idea_expansion(
        venture_positioning, feature_gap, mvp_recommendation, (startup.market_evidence if startup is not None else None) or {}
    )
    context = build_idea_expansion_context(
        startup_name, startup_description, venture_positioning, feature_gap, mvp_recommendation, funding_level
    )
    return generate_idea_expansion_safely(context, baseline)


def _regenerate_strategic_opportunity(
    mentor_interpretation: dict | None,
    judge_summary: dict | None,
    startup: Startup | None,
    analysis: Analysis,
) -> dict | None:
    """Rebuild `strategic_opportunity` from a just-regenerated `mentor_interpretation` — called
    after `_regenerate_mentor_interpretation`/`_regenerate_idea_expansion` in both correction
    helpers below so a positioning/revenue correction never leaves a stale Strategic Opportunity
    (adjacent markets/risks derived from the now-outdated venture_positioning) behind.

    Returns None if there is no mentor_interpretation to derive from yet.
    """
    if mentor_interpretation is None:
        return None

    startup_name = startup.name if startup is not None else ""
    startup_description = startup.description if startup is not None else ""
    venture_positioning = (judge_summary or {}).get("venture_positioning") or {}
    feature_gap = mentor_interpretation.get("feature_gap_analysis") or {}
    founder_guidance_items = mentor_interpretation.get("founder_guidance_items") or []
    funding_level = (mentor_interpretation.get("mentor_verdict") or {}).get("readiness_level", "early_stage")

    baseline = build_deterministic_strategic_opportunity(
        venture_positioning, analysis.market_intelligence, analysis.customer_personas,
        analysis.business_model, analysis.competitor_analysis, feature_gap,
        founder_guidance_items, analysis.funding_assessment or {},
    )
    context = build_strategic_opportunity_context(
        startup_name, startup_description, venture_positioning, analysis.market_intelligence,
        analysis.business_model, analysis.competitor_analysis, feature_gap, funding_level,
    )
    return generate_strategic_opportunity_safely(context, baseline)


def create_startup(db: Session, payload: StartupCreateRequest) -> Startup:
    now = datetime.now(timezone.utc)
    startup = Startup(
        name=payload.name,
        description=payload.description,
        funding_answers=payload.funding_answers.model_dump(),
        company_metrics=payload.company_metrics.model_dump(),
        revenue_assumptions=payload.revenue_assumptions.model_dump(),
        market_evidence=payload.market_evidence.model_dump(),
        customer_rfm=payload.customer_rfm.model_dump() if payload.customer_rfm else None,
        created_at=now,
        updated_at=now,
    )
    db.add(startup)
    db.commit()
    db.refresh(startup)
    return startup


def get_startup(db: Session, startup_id: uuid.UUID) -> Startup | None:
    return db.get(Startup, startup_id)


def get_analysis(db: Session, analysis_id: uuid.UUID) -> Analysis | None:
    return db.get(Analysis, analysis_id)


def run_analysis_for_startup(db: Session, startup: Startup) -> Analysis:
    """Run the orchestrator synchronously and persist the result as a new Analysis row."""
    now = datetime.now(timezone.utc)
    analysis = Analysis(startup_id=startup.id, status="PENDING", created_at=now, updated_at=now)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    def persist(state: OrchestratorState) -> None:
        industry = state.get("industry_prediction")
        funding = state.get("funding_assessment")
        analysis.status = state.get("status", "FAILED")
        analysis.industry_prediction = industry
        analysis.industry_model_version = industry.get("model_version") if industry else None
        analysis.funding_assessment = funding
        analysis.funding_rubric_version = funding.get("rubric_version") if funding else None

        success_prediction = state.get("success_prediction")
        analysis.success_prediction = success_prediction
        analysis.success_model_version = success_prediction.get("model_version") if success_prediction else None

        revenue_estimate = state.get("revenue_estimate")
        analysis.revenue_estimate = revenue_estimate
        analysis.revenue_engine_version = revenue_estimate.get("engine_version") if revenue_estimate else None

        analysis.market_intelligence = state.get("market_intelligence")
        analysis.competitor_analysis = state.get("competitor_analysis")
        analysis.customer_personas = state.get("customer_personas")
        analysis.business_model = state.get("business_model")

        analysis.judge_summary = state.get("judge_summary")
        analysis.mentor_interpretation = state.get("mentor_interpretation")
        analysis.idea_expansion = state.get("idea_expansion")
        analysis.strategic_opportunity = state.get("strategic_opportunity")

        # Phase 5 (Student 3): additive growth/strategy intelligence — see app.agents.student3.
        # Only assembled for a run that reached funding_readiness (customer_segment is always a
        # dict once that node has run); null for a run that failed before then.
        customer_segment = state.get("customer_segment")
        if customer_segment is not None:
            analysis.student3_outputs = Student3Outputs(
                customer_segment=customer_segment,
                ranked_actions=state.get("ranked_actions") or [],
                innovation_opportunities=state.get("innovation_opportunities") or [],
                risks=state.get("risk_assessment") or [],
                growth_strategy=state.get("growth_strategy") or [],
                pitch_deck=state.get("pitch_deck") or [],
                executive_summary=[(state.get("judge_summary") or {}).get("overall_assessment", "")],
            ).model_dump()
        else:
            analysis.student3_outputs = None

        analysis.workflow_trace = state.get("trace")
        analysis.error_message = state.get("error")
        analysis.updated_at = datetime.now(timezone.utc)
        db.add(analysis)
        db.commit()

    run_pipeline(
        startup_name=startup.name,
        startup_description=startup.description,
        funding_answers=startup.funding_answers,
        persist_fn=persist,
        company_metrics=startup.company_metrics,
        revenue_assumptions=startup.revenue_assumptions,
        market_evidence=startup.market_evidence,
        customer_rfm=startup.customer_rfm,
    )
    db.refresh(analysis)
    return analysis


def apply_industry_correction(
    db: Session, analysis_id: uuid.UUID, primary_domain: str, secondary_domains: list[str]
) -> Analysis | None:
    """Rerun the deterministic Judge resolution with a founder-submitted `user_override` (see
    app.agents.venture_positioning.resolve_venture_positioning — `user_override` always wins).
    Never touches `model_category` (the raw trained-classifier output). Appends one entry to
    `positioning_correction_history`; never mutates or removes a prior entry. Also regenerates
    `mentor_interpretation` (see `_regenerate_mentor_interpretation`) so the mentor narrative never
    lags a just-applied positioning correction.

    Returns None if the analysis doesn't exist — callers translate that to a 404.
    """
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        return None
    startup = db.get(Startup, analysis.startup_id)

    judge_summary = dict(analysis.judge_summary or {})
    previous_positioning = judge_summary.get("venture_positioning")
    model_category = judge_summary.get("model_category") or build_model_category(analysis.industry_prediction)

    taxonomy_result = score_taxonomy(startup.description if startup is not None else "")
    resolution = resolve_venture_positioning(
        taxonomy_result, model_category, gemini_recommendation=None, user_override=primary_domain
    )
    new_positioning = resolution["venture_positioning"]
    if secondary_domains:
        new_positioning["secondary_domains"] = secondary_domains

    now = datetime.now(timezone.utc)
    history_entry = {
        "previous_positioning": previous_positioning,
        "override": {"primary_domain": primary_domain, "secondary_domains": secondary_domains},
        "taxonomy_version": TAXONOMY_VERSION,
        "corrected_at": now.isoformat(),
    }

    judge_summary["venture_positioning"] = new_positioning
    judge_summary["positioning_correction_rationale"] = resolution["correction_rationale"]
    analysis.judge_summary = judge_summary
    analysis.positioning_correction_history = [*(analysis.positioning_correction_history or []), history_entry]
    analysis.mentor_interpretation = _regenerate_mentor_interpretation(analysis, startup)
    analysis.idea_expansion = _regenerate_idea_expansion(analysis.mentor_interpretation, judge_summary, startup)
    analysis.strategic_opportunity = _regenerate_strategic_opportunity(analysis.mentor_interpretation, judge_summary, startup, analysis)
    analysis.updated_at = now
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def apply_revenue_assumptions_update(
    db: Session, analysis_id: uuid.UUID, updates: dict[str, float | None]
) -> Analysis | None:
    """Persist a partial (or complete) edit to the founder's revenue assumptions and recompute the
    conservative/base/optimistic scenarios server-side.

    `updates` should come from `RevenueAssumptionsPatchRequest.model_dump(exclude_unset=True)` —
    only keys the caller actually included in the request body. A key present with value `None`
    explicitly clears that assumption (falls back to a suggested default on the next
    `estimate_revenue_scenario` call); a key simply absent from `updates` is left untouched.

    Never touches `model_category` or `venture_positioning` — this is a revenue-only edit. Appends
    one entry to `revenue_assumptions_history`; never mutates or removes a prior entry. Also
    regenerates `mentor_interpretation` (see `_regenerate_mentor_interpretation`) so its revenue
    narrative never lags a just-saved assumption edit. Returns None if the analysis doesn't
    exist — callers translate that to a 404.
    """
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        return None
    startup = db.get(Startup, analysis.startup_id)

    previous_assumptions = dict(startup.revenue_assumptions or {}) if startup is not None else {}
    updated_assumptions = dict(previous_assumptions)
    for field, value in updates.items():
        if value is None:
            updated_assumptions.pop(field, None)
        else:
            updated_assumptions[field] = value

    judge_summary = analysis.judge_summary or {}
    venture_positioning = judge_summary.get("venture_positioning") or {}
    model_category = judge_summary.get("model_category") or {}

    new_revenue_estimate = estimate_revenue_scenario(
        updated_assumptions.get("price_per_customer_usd"),
        updated_assumptions.get("initial_customers"),
        updated_assumptions.get("monthly_growth_rate_pct"),
        updated_assumptions.get("gross_margin_pct"),
        primary_domain=venture_positioning.get("primary_domain"),
        model_category_label=model_category.get("label"),
    )

    now = datetime.now(timezone.utc)
    history_entry = {
        "previous_assumptions": previous_assumptions,
        "updated_assumptions": updated_assumptions,
        "changed_fields": sorted(updates.keys()),
        "updated_at": now.isoformat(),
    }

    if startup is not None:
        startup.revenue_assumptions = updated_assumptions
        startup.updated_at = now
        db.add(startup)

    analysis.revenue_estimate = new_revenue_estimate
    analysis.revenue_engine_version = new_revenue_estimate.get("engine_version")
    analysis.revenue_assumptions_history = [*(analysis.revenue_assumptions_history or []), history_entry]
    analysis.mentor_interpretation = _regenerate_mentor_interpretation(analysis, startup)
    analysis.idea_expansion = _regenerate_idea_expansion(analysis.mentor_interpretation, judge_summary, startup)
    analysis.strategic_opportunity = _regenerate_strategic_opportunity(analysis.mentor_interpretation, judge_summary, startup, analysis)
    analysis.updated_at = now
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis
