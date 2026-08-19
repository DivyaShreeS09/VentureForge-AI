"""LangGraph orchestrator wiring the 7 required nodes for the Student 1 vertical slice:

    input_validation -> industry_classification -> funding_readiness
        -> evidence_confidence_check -> judge -> persistence -> final_response

Routing is deterministic: an invalid input short-circuits straight to final_response with a
FAILED status. No node calls another agent directly, no loops, no external API is required.

Extension point for Student 2 / Student 3: additional nodes (startup success prediction, revenue
estimation, market intelligence, competitor analysis, customer persona, business model, customer
segmentation, innovation, risk, growth, pitch) can be inserted between `funding_readiness` and
`judge` by adding them to the graph and updating `judge.synthesize` to accept their output — the
typed `OrchestratorState` in state.py is additive (TypedDict, total=False) so new keys don't break
existing nodes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents import judge as judge_agent
from app.agents.causal_reasoning import build_causal_reasoning
from app.agents.counterfactual_simulation import build_counterfactual_simulation
from app.agents.decision_synthesis import build_decision_synthesis
from app.agents.nodes import (
    assess_risks_node,
    build_pitch_deck_node,
    business_model_node,
    competitor_analysis_node,
    customer_persona_node,
    evidence_confidence_check_node,
    funding_readiness_node,
    idea_expansion_node,
    industry_classification_node,
    input_validation_node,
    market_analysis_node,
    mentor_synthesis_node,
    plan_growth_strategy_node,
    rank_actions_node,
    revenue_estimate_node,
    segment_customers_node,
    strategic_opportunity_node,
    success_prediction_node,
    surface_innovation_node,
    venture_positioning_node,
)
from app.agents.state import OrchestratorState
from app.ai.base import LLMUnavailable
from app.ai.factory import get_llm_provider
from app.ai.schemas import NarrativeContext

logger = logging.getLogger(__name__)

PersistFn = Callable[[OrchestratorState], None]


def _try_llm_narrative(
    industry_prediction: dict | None, funding_assessment: dict, judge_summary: dict, state: OrchestratorState
) -> dict | None:
    """Best-effort optional narrative enhancement. Returns None whenever no provider is
    configured, the call fails, times out, or returns something that fails schema validation —
    every one of those is a normal, expected outcome (most users will never set GEMINI_API_KEY),
    not an error condition that should affect the rest of the pipeline.
    """
    provider = get_llm_provider()
    if provider is None:
        return None

    try:
        context = NarrativeContext(
            startup_name=state.get("startup_name") or "",
            startup_description=state.get("startup_description") or "",
            predicted_industry=(industry_prediction or {}).get("predicted_industry", "unknown"),
            industry_confidence=(industry_prediction or {}).get("confidence", 0.0),
            industry_is_uncertain=(industry_prediction or {}).get("is_uncertain", True),
            funding_score=funding_assessment.get("overall_score", 0),
            funding_level=funding_assessment.get("level", "unknown"),
            strengths=judge_summary.get("strengths", []),
            weaknesses=judge_summary.get("weaknesses", []),
            missing_evidence=judge_summary.get("missing_evidence", []),
        )
        narrative = provider.generate_narrative(context)
        return narrative.model_dump()
    except LLMUnavailable as exc:
        logger.info("LLM narrative unavailable, falling back to deterministic output: %s", exc)
        return None
    except Exception:
        # Any other unexpected error (including one raised by a future third-party provider) must
        # never take down the deterministic pipeline — this is the one path where a bare except
        # is intentional: the LLM layer is additive and optional by design.
        logger.exception("Unexpected error generating LLM narrative; falling back")
        return None


def _judge_node(state: OrchestratorState) -> dict:
    try:
        industry_prediction = state.get("industry_prediction")
        funding_assessment = state.get("funding_assessment") or {}
        summary = judge_agent.synthesize(
            industry_prediction,
            funding_assessment,
            state.get("evidence_check") or {},
            success_prediction=state.get("success_prediction"),
            revenue_estimate=state.get("revenue_estimate"),
            market_intelligence=state.get("market_intelligence"),
            competitor_analysis=state.get("competitor_analysis"),
            customer_personas=state.get("customer_personas"),
            business_model=state.get("business_model"),
            model_category=state.get("model_category"),
            venture_positioning=state.get("venture_positioning"),
            taxonomy_candidates=state.get("taxonomy_candidates"),
            gemini_structured_recommendation=state.get("gemini_structured_recommendation"),
            gemini_rationale=state.get("gemini_rationale"),
            positioning_correction_rationale=state.get("positioning_correction_rationale"),
            market_evidence=state.get("market_evidence"),
            customer_segment=state.get("customer_segment"),
            ranked_actions=state.get("ranked_actions"),
            risks=state.get("risk_assessment"),
            startup_name=state.get("startup_name") or "",
            startup_description=state.get("startup_description") or "",
        )
        summary["llm_narrative"] = _try_llm_narrative(industry_prediction, funding_assessment, summary, state)
        return {"judge_summary": summary, "trace": [{"node": "judge", "status": "ok", "detail": None}]}
    except ValueError as exc:
        return {
            "judge_summary": None,
            "status": "FAILED",
            "error": str(exc),
            "trace": [{"node": "judge", "status": "error", "detail": str(exc)}],
        }


def _decision_synthesis_node(state: OrchestratorState) -> dict:
    """VentureForge Intelligence Architecture, Phase I: the central reasoning brain, run last (it
    is the only node with access to every other structured output — see
    app.agents.decision_synthesis for the full audit of what it reasons across and why). Purely
    additive: merges one new `decision_synthesis` key into the existing `judge_summary` dict — the
    same pattern app.services.analysis_service already uses for founder-initiated corrections
    (`judge_summary["venture_positioning"] = ...`) — rather than a new persisted column, so no
    endpoint or schema changes are required to expose it.
    """
    judge_summary = state.get("judge_summary")
    if judge_summary is None:
        return {"trace": [{"node": "decision_synthesis", "status": "skipped", "detail": "judge_summary unavailable"}]}

    decision_synthesis = build_decision_synthesis(
        evidence_ledger=judge_summary.get("evidence_ledger"),
        evidence_ledger_summary=judge_summary.get("evidence_ledger_summary"),
        venture_frame=judge_summary.get("venture_frame"),
        hypothesis_set=judge_summary.get("hypothesis_set"),
        contradiction_set=judge_summary.get("contradiction_set"),
        alternative_explanation_set=judge_summary.get("alternative_explanation_set"),
        funding_assessment=state.get("funding_assessment"),
        industry_prediction=state.get("industry_prediction"),
        success_prediction=state.get("success_prediction"),
        strategic_opportunity=state.get("strategic_opportunity"),
        founder_guidance_items=judge_summary.get("founder_guidance_items"),
        ranked_actions=state.get("ranked_actions"),
        risk_assessment=state.get("risk_assessment"),
    )
    updated_summary = {**judge_summary, "decision_synthesis": decision_synthesis}
    return {
        "judge_summary": updated_summary,
        "trace": [{"node": "decision_synthesis", "status": "ok", "detail": None}],
    }


def _causal_reasoning_node(state: OrchestratorState) -> dict:
    """VentureForge Intelligence Architecture, Phase H: explains *why*, as explicit CauseEffectChain
    objects, rather than recomputing what Decision Synthesis already resolved — see
    app.agents.causal_reasoning for the full audit of what it reuses versus what it newly reasons
    across. Purely additive: merges one new `causal_reasoning` key into the existing `judge_summary`
    dict, the same pattern Phase I already established for `decision_synthesis` — no endpoint or
    schema changes required.
    """
    judge_summary = state.get("judge_summary")
    if judge_summary is None:
        return {"trace": [{"node": "causal_reasoning", "status": "skipped", "detail": "judge_summary unavailable"}]}

    causal_reasoning = build_causal_reasoning(
        decision_synthesis=judge_summary.get("decision_synthesis"),
        venture_frame=judge_summary.get("venture_frame"),
        funding_assessment=state.get("funding_assessment"),
        strategic_opportunity=state.get("strategic_opportunity"),
        founder_guidance_items=judge_summary.get("founder_guidance_items"),
    )
    updated_summary = {**judge_summary, "causal_reasoning": causal_reasoning}
    return {
        "judge_summary": updated_summary,
        "trace": [{"node": "causal_reasoning", "status": "ok", "detail": None}],
    }


def _counterfactual_simulation_node(state: OrchestratorState) -> dict:
    """VentureForge Intelligence Architecture, Phase G: deterministic "what-if" reasoning that
    actually re-invokes the existing pipeline functions with one evidence item surgically changed
    — see app.agents.counterfactual_simulation for the full audit of what is recomputed for real
    versus held constant, and why. Purely additive: merges one new `counterfactual_simulation` key
    into the existing `judge_summary` dict, the same pattern Phases H/I already established.
    """
    judge_summary = state.get("judge_summary")
    if judge_summary is None:
        return {"trace": [{"node": "counterfactual_simulation", "status": "skipped", "detail": "judge_summary unavailable"}]}

    counterfactual_simulation = build_counterfactual_simulation(
        evidence_ledger=judge_summary.get("evidence_ledger"),
        venture_frame=judge_summary.get("venture_frame"),
        funding_assessment=state.get("funding_assessment"),
        decision_synthesis=judge_summary.get("decision_synthesis"),
        causal_reasoning=judge_summary.get("causal_reasoning"),
        hypothesis_set=judge_summary.get("hypothesis_set"),
        contradiction_set=judge_summary.get("contradiction_set"),
        alternative_explanation_set=judge_summary.get("alternative_explanation_set"),
        strategic_opportunity=state.get("strategic_opportunity"),
        founder_guidance_items=judge_summary.get("founder_guidance_items"),
        ranked_actions=state.get("ranked_actions"),
        risk_assessment=state.get("risk_assessment"),
    )
    updated_summary = {**judge_summary, "counterfactual_simulation": counterfactual_simulation}
    return {
        "judge_summary": updated_summary,
        "trace": [{"node": "counterfactual_simulation", "status": "ok", "detail": None}],
    }


def _make_persistence_node(persist_fn: PersistFn | None) -> Callable[[OrchestratorState], dict]:
    def persistence_node(state: OrchestratorState) -> dict:
        # The run is terminal here: either an upstream node already set FAILED, or every prior
        # node succeeded and the run is COMPLETED. Persistence is the single place that decides
        # and saves this terminal status — final_response only formats what was just persisted.
        final_status = "FAILED" if state.get("status") == "FAILED" else "COMPLETED"
        persisted_state = {**state, "status": final_status}
        if persist_fn is not None:
            persist_fn(persisted_state)
        return {
            "status": final_status,
            "trace": [{"node": "persistence", "status": "ok", "detail": None}],
        }

    return persistence_node


def _final_response_node(state: OrchestratorState) -> dict:
    # Status was already finalized and persisted by the persistence node; this node only formats
    # the trace entry, it does not change status.
    detail = "run failed upstream" if state.get("status") == "FAILED" else None
    return {"trace": [{"node": "final_response", "status": "ok", "detail": detail}]}


def _route_after_validation(state: OrchestratorState) -> str:
    return "continue" if state["validation"]["valid"] else "invalid"


def _invalid_input_node(state: OrchestratorState) -> dict:
    return {
        "status": "FAILED",
        "error": "; ".join(state["validation"]["errors"]),
        "trace": [{"node": "invalid_input", "status": "error", "detail": None}],
    }


def build_graph(persist_fn: PersistFn | None = None):
    graph = StateGraph(OrchestratorState)

    graph.add_node("input_validation", input_validation_node)
    graph.add_node("invalid_input", _invalid_input_node)
    graph.add_node("industry_classification", industry_classification_node)
    graph.add_node("funding_readiness", funding_readiness_node)
    # Node ids below are deliberately distinct from their OrchestratorState output keys (e.g.
    # "predict_success" vs the `success_prediction` state field) — LangGraph rejects a node id
    # that collides with an existing state key.
    graph.add_node("predict_success", success_prediction_node)
    graph.add_node("estimate_revenue", revenue_estimate_node)
    graph.add_node("analyze_market", market_analysis_node)
    graph.add_node("analyze_competitors", competitor_analysis_node)
    graph.add_node("build_customer_persona", customer_persona_node)
    graph.add_node("evaluate_business_model", business_model_node)
    graph.add_node("resolve_venture_positioning", venture_positioning_node)
    # Phase 5 (Student 3) — deterministic growth/strategy planning nodes, additively spliced
    # between the Student 2 chain and evidence_confidence_check. Node ids are deliberately
    # distinct from the OrchestratorState keys they populate (see the "predict_success" comment
    # above for why LangGraph requires this).
    graph.add_node("segment_customers", segment_customers_node)
    graph.add_node("rank_actions", rank_actions_node)
    graph.add_node("surface_innovation", surface_innovation_node)
    graph.add_node("assess_risks", assess_risks_node)
    graph.add_node("plan_growth_strategy", plan_growth_strategy_node)
    graph.add_node("build_pitch_deck", build_pitch_deck_node)
    graph.add_node("evidence_confidence_check", evidence_confidence_check_node)
    graph.add_node("judge", _judge_node)
    graph.add_node("mentor_synthesis", mentor_synthesis_node)
    # Node id deliberately distinct from the `idea_expansion` state key (see the comment above on
    # "predict_success" vs `success_prediction` for why LangGraph requires this).
    graph.add_node("expand_ideas", idea_expansion_node)
    # Node id deliberately distinct from the `strategic_opportunity` state key, same reason.
    graph.add_node("discover_strategic_opportunities", strategic_opportunity_node)
    graph.add_node("synthesize_decision", _decision_synthesis_node)
    graph.add_node("reason_causally", _causal_reasoning_node)
    graph.add_node("simulate_counterfactuals", _counterfactual_simulation_node)
    graph.add_node("persistence", _make_persistence_node(persist_fn))
    graph.add_node("final_response", _final_response_node)

    graph.set_entry_point("input_validation")
    graph.add_conditional_edges(
        "input_validation",
        _route_after_validation,
        {"continue": "industry_classification", "invalid": "invalid_input"},
    )
    graph.add_edge("invalid_input", "persistence")
    # `resolve_venture_positioning` only needs `industry_prediction` + `startup_description` — it
    # runs right after industry classification (not at the end) so `estimate_revenue` and
    # `analyze_competitors` can key their deterministic defaults/suggestions off
    # `venture_positioning.primary_domain`.
    graph.add_edge("industry_classification", "resolve_venture_positioning")
    graph.add_edge("resolve_venture_positioning", "funding_readiness")
    graph.add_edge("funding_readiness", "predict_success")
    graph.add_edge("predict_success", "estimate_revenue")
    graph.add_edge("estimate_revenue", "analyze_market")
    graph.add_edge("analyze_market", "analyze_competitors")
    graph.add_edge("analyze_competitors", "build_customer_persona")
    graph.add_edge("build_customer_persona", "evaluate_business_model")
    graph.add_edge("evaluate_business_model", "segment_customers")
    graph.add_edge("segment_customers", "rank_actions")
    graph.add_edge("rank_actions", "surface_innovation")
    graph.add_edge("surface_innovation", "assess_risks")
    graph.add_edge("assess_risks", "plan_growth_strategy")
    graph.add_edge("plan_growth_strategy", "build_pitch_deck")
    graph.add_edge("build_pitch_deck", "evidence_confidence_check")
    graph.add_edge("evidence_confidence_check", "judge")
    graph.add_edge("judge", "mentor_synthesis")
    graph.add_edge("mentor_synthesis", "expand_ideas")
    graph.add_edge("expand_ideas", "discover_strategic_opportunities")
    graph.add_edge("discover_strategic_opportunities", "synthesize_decision")
    graph.add_edge("synthesize_decision", "reason_causally")
    graph.add_edge("reason_causally", "simulate_counterfactuals")
    graph.add_edge("simulate_counterfactuals", "persistence")
    graph.add_edge("persistence", "final_response")
    graph.add_edge("final_response", END)

    return graph.compile()


def _initial_state(
    startup_name: str,
    startup_description: str,
    funding_answers: dict[str, int | None],
    company_metrics: dict[str, Any] | None,
    revenue_assumptions: dict[str, Any] | None,
    market_evidence: dict[str, Any] | None,
    customer_rfm: dict[str, float] | None,
) -> OrchestratorState:
    return {
        "startup_name": startup_name,
        "startup_description": startup_description,
        "funding_answers": funding_answers,
        "company_metrics": company_metrics or {},
        "revenue_assumptions": revenue_assumptions or {},
        "market_evidence": market_evidence or {},
        "customer_rfm": customer_rfm,
        "status": "RUNNING",
        "error": None,
        "trace": [],
    }


def run_pipeline(
    startup_name: str,
    startup_description: str,
    funding_answers: dict[str, int | None],
    persist_fn: PersistFn | None = None,
    company_metrics: dict[str, Any] | None = None,
    revenue_assumptions: dict[str, Any] | None = None,
    market_evidence: dict[str, Any] | None = None,
    customer_rfm: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run the full orchestration pipeline synchronously (blocking until every node has run) and
    return the final state. Used directly by tests exercising the orchestrator in isolation; the
    live API path uses `stream_pipeline` below instead (same graph, same nodes — see its
    docstring) so The Forging can observe real per-node completion as it happens."""
    compiled = build_graph(persist_fn)
    initial_state = _initial_state(
        startup_name, startup_description, funding_answers, company_metrics, revenue_assumptions,
        market_evidence, customer_rfm,
    )
    # LangGraph's default recursion_limit (25) counts every super-step, i.e. every node in this
    # linear graph — Phase H's two additive nodes (synthesize_decision, reason_causally) pushed the
    # real node count to exactly that boundary. Raised with headroom rather than tuned to the exact
    # current count, so a future additive node doesn't silently reintroduce this failure.
    return compiled.invoke(initial_state, config={"recursion_limit": 100})


def stream_pipeline(
    startup_name: str,
    startup_description: str,
    funding_answers: dict[str, int | None],
    company_metrics: dict[str, Any] | None = None,
    revenue_assumptions: dict[str, Any] | None = None,
    market_evidence: dict[str, Any] | None = None,
    customer_rfm: dict[str, float] | None = None,
):
    """Runs the exact same compiled graph as `run_pipeline` (no second pipeline, no duplicated
    orchestration or node logic — `build_graph` is the single source of truth for both), but
    yields `(node_name, state_delta)` as each node completes instead of blocking until the whole
    run finishes. This is LangGraph's own native `stream_mode="updates"` — a real capability
    already built into the framework already in use, not a new AI capability or a second
    prediction path. `persist_fn` is intentionally not wired into this graph build: the caller
    (see `analysis_service._execute_analysis_stream`) persists each yielded delta itself, since it
    alone knows how to merge deltas into cumulative state and publish live-progress events.
    """
    compiled = build_graph(persist_fn=None)
    initial_state = _initial_state(
        startup_name, startup_description, funding_answers, company_metrics, revenue_assumptions,
        market_evidence, customer_rfm,
    )
    # See run_pipeline's matching comment on recursion_limit above — same graph, same fix.
    for update in compiled.stream(initial_state, stream_mode="updates", config={"recursion_limit": 100}):
        for node_name, delta in update.items():
            yield node_name, delta
