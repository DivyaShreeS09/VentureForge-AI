"""Business logic for creating startups and running/persisting their analysis pipeline."""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.agents.idea_expansion import build_deterministic_idea_expansion
from app.agents.idea_expansion_reviewer import build_idea_expansion_context, generate_idea_expansion_safely
from app.agents.mentor_reviewer import build_mentor_context, review_mentor_safely
from app.agents.mentor_synthesis import build_deterministic_mentor
from app.agents.orchestrator import stream_pipeline
from app.agents.stage_labels import stage_label_for
from app.agents.strategic_opportunity import build_deterministic_strategic_opportunity
from app.agents.strategic_opportunity_reviewer import (
    build_strategic_opportunity_context,
    generate_strategic_opportunity_safely,
)
from app.agents.venture_positioning import build_model_category, resolve_venture_positioning
from app.ml.positioning_taxonomy import TAXONOMY_VERSION, score_taxonomy
from app.ml.revenue_scenario import estimate_revenue_scenario
from app.models.analysis import Analysis
from app.models.startup import Startup
from app.schemas.startup import StartupCreateRequest
from app.schemas.student3 import Student3Outputs
from app.services import analysis_events

logger = logging.getLogger(__name__)


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


def start_analysis_for_startup(db: Session, startup: Startup, session_factory: sessionmaker) -> Analysis:
    """Act IV (The Forging): creates the Analysis row and returns it immediately (status
    RUNNING, no fields populated yet) — the real orchestrator run happens in a background thread
    (`_execute_analysis_stream`), reusing the exact same compiled graph as the synchronous
    `run_pipeline` (via `stream_pipeline`), just observed and persisted incrementally after every
    real node completes instead of only once at the end. This is what lets the frontend show
    genuine, real intermediate progress instead of one long blocking call followed by an
    all-at-once reveal.
    """
    now = datetime.now(timezone.utc)
    analysis = Analysis(startup_id=startup.id, status="RUNNING", created_at=now, updated_at=now)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    thread = threading.Thread(
        target=_execute_analysis_stream,
        args=(
            analysis.id,
            startup.name,
            startup.description,
            startup.funding_answers,
            startup.company_metrics,
            startup.revenue_assumptions,
            startup.market_evidence,
            startup.customer_rfm,
            session_factory,
        ),
        daemon=True,
    )
    thread.start()
    return analysis


def _execute_analysis_stream(
    analysis_id: uuid.UUID,
    startup_name: str,
    startup_description: str,
    funding_answers: dict[str, Any],
    company_metrics: dict[str, Any],
    revenue_assumptions: dict[str, Any],
    market_evidence: dict[str, Any],
    customer_rfm: dict[str, float] | None,
    session_factory: sessionmaker,
) -> None:
    """Runs on a background thread with its own DB session (a request-scoped session can't cross
    threads). Consumes `stream_pipeline`'s real per-node updates, merges each into a running
    cumulative state (mirroring the `trace` key's additive-reducer semantics LangGraph itself
    applies during a normal `.invoke()` — `stream_mode="updates"` intentionally yields each node's
    own raw delta, not the pre-merged state), persists the real, currently-known fields after
    every single node, and wakes any SSE subscriber via `analysis_events.publish`.
    """
    db = session_factory()
    accumulated: dict[str, Any] = {"trace": []}
    try:
        for node_name, delta in stream_pipeline(
            startup_name=startup_name,
            startup_description=startup_description,
            funding_answers=funding_answers,
            company_metrics=company_metrics,
            revenue_assumptions=revenue_assumptions,
            market_evidence=market_evidence,
            customer_rfm=customer_rfm,
        ):
            for key, value in delta.items():
                if key == "trace":
                    accumulated.setdefault("trace", []).extend(value)
                else:
                    accumulated[key] = value
            _persist_progress(db, analysis_id, node_name, accumulated)
            analysis_events.publish(str(analysis_id), {"node": node_name})
            # "persistence" is the graph's single terminal-status node (see
            # orchestrator.py's `_make_persistence_node`) — the only node after it,
            # "final_response", only formats a trace entry and changes nothing a founder needs to
            # see. Stopping here (rather than continuing to pull one more, meaningless update from
            # the generator) avoids a harmless-but-real race: a caller who already observed the
            # terminal status via GET/SSE may reasonably consider the run finished and tear down
            # resources (exactly what the test suite does) before this thread gets to it.
            if node_name == "persistence":
                break
    except Exception as exc:  # noqa: BLE001 - a background thread must never crash silently and
        # leave an analysis permanently stuck "RUNNING"; this is the one intentional bare-except
        # here, mirroring orchestrator.py's own single bare-except for the optional LLM layer.
        logger.exception("Unexpected error during background analysis run for %s", analysis_id)
        analysis = db.get(Analysis, analysis_id)
        if analysis is not None:
            analysis.status = "FAILED"
            analysis.error_message = f"Unexpected error: {exc}"
            analysis.updated_at = datetime.now(timezone.utc)
            db.add(analysis)
            db.commit()
        analysis_events.publish(str(analysis_id), {"node": "error"})
    finally:
        db.close()


def _persist_progress(db: Session, analysis_id: uuid.UUID, node_name: str, state: dict[str, Any]) -> None:
    """Persists whichever real fields are present in the cumulative state so far — every field
    here is one `Analysis` already stores (see `run_analysis_for_startup`'s pre-Sprint-6
    equivalent, now applied per-node instead of once). Never invents an "intermediate_outputs"
    blob: a founder sees `industry_prediction` the moment industry classification really
    finishes, `judge_summary` the moment the Judge really finishes, and so on."""
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        return

    analysis.current_node = node_name
    analysis.current_stage = stage_label_for(node_name)

    if "industry_prediction" in state:
        industry = state.get("industry_prediction")
        analysis.industry_prediction = industry
        analysis.industry_model_version = industry.get("model_version") if industry else None
    if "funding_assessment" in state:
        funding = state.get("funding_assessment")
        analysis.funding_assessment = funding
        analysis.funding_rubric_version = funding.get("rubric_version") if funding else None
    if "success_prediction" in state:
        success_prediction = state.get("success_prediction")
        analysis.success_prediction = success_prediction
        analysis.success_model_version = success_prediction.get("model_version") if success_prediction else None
    if "revenue_estimate" in state:
        revenue_estimate = state.get("revenue_estimate")
        analysis.revenue_estimate = revenue_estimate
        analysis.revenue_engine_version = revenue_estimate.get("engine_version") if revenue_estimate else None
    if "market_intelligence" in state:
        analysis.market_intelligence = state.get("market_intelligence")
    if "competitor_analysis" in state:
        analysis.competitor_analysis = state.get("competitor_analysis")
    if "customer_personas" in state:
        analysis.customer_personas = state.get("customer_personas")
    if "business_model" in state:
        analysis.business_model = state.get("business_model")
    if "judge_summary" in state:
        analysis.judge_summary = state.get("judge_summary")
    if "mentor_interpretation" in state:
        analysis.mentor_interpretation = state.get("mentor_interpretation")
    if "idea_expansion" in state:
        analysis.idea_expansion = state.get("idea_expansion")
    if "strategic_opportunity" in state:
        analysis.strategic_opportunity = state.get("strategic_opportunity")

    # Phase 5 (Student 3): rebuilt on every node from this point on so it progressively fills in
    # (ranked_actions/risks/etc. each arrive from a later node) rather than appearing all at once.
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

    analysis.workflow_trace = state.get("trace")
    if state.get("error"):
        analysis.error_message = state.get("error")

    # The "persistence" node is the single place the graph decides the terminal status (see
    # orchestrator.py's `_make_persistence_node`) — its own delta always carries the real,
    # authoritative COMPLETED/FAILED value.
    if node_name == "persistence":
        analysis.status = state.get("status", "FAILED")

    analysis.updated_at = datetime.now(timezone.utc)
    db.add(analysis)
    db.commit()


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
