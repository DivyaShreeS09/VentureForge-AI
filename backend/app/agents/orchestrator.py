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
from app.agents.nodes import (
    evidence_confidence_check_node,
    funding_readiness_node,
    industry_classification_node,
    input_validation_node,
    market_analysis_node,
    competitor_analysis_node,
    customer_persona_node,
    business_model_node,
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
    graph.add_node("market_analysis", market_analysis_node)
    graph.add_node("competitor_analysis", competitor_analysis_node)
    graph.add_node("customer_persona", customer_persona_node)
    graph.add_node("business_model", business_model_node)
    graph.add_node("evidence_confidence_check", evidence_confidence_check_node)
    graph.add_node("judge", _judge_node)
    graph.add_node("persistence", _make_persistence_node(persist_fn))
    graph.add_node("final_response", _final_response_node)

    graph.set_entry_point("input_validation")
    graph.add_conditional_edges(
        "input_validation",
        _route_after_validation,
        {"continue": "industry_classification", "invalid": "invalid_input"},
    )
    graph.add_edge("invalid_input", "persistence")
    graph.add_edge("industry_classification", "funding_readiness")
    graph.add_edge("funding_readiness", "evidence_confidence_check")
    graph.add_edge("funding_readiness", "market_analysis")
    graph.add_edge("market_analysis", "competitor_analysis")
    graph.add_edge("competitor_analysis", "customer_persona")
    graph.add_edge("customer_persona", "business_model")
    graph.add_edge("business_model", "evidence_confidence_check")
    graph.add_edge("evidence_confidence_check", "judge")
    graph.add_edge("judge", "persistence")
    graph.add_edge("persistence", "final_response")
    graph.add_edge("final_response", END)

    return graph.compile()


def run_pipeline(
    startup_name: str,
    startup_description: str,
    funding_answers: dict[str, int | None],
    persist_fn: PersistFn | None = None,
) -> dict[str, Any]:
    """Run the full orchestration pipeline synchronously and return the final state."""
    compiled = build_graph(persist_fn)
    initial_state: OrchestratorState = {
        "startup_name": startup_name,
        "startup_description": startup_description,
        "funding_answers": funding_answers,
        "status": "RUNNING",
        "error": None,
        "trace": [],
    }
    return compiled.invoke(initial_state)
