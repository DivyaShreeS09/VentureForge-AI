"""Orchestrator node functions. Each is a plain, independently-testable function: takes the
current state, returns the keys it updates (LangGraph merges these into state). No node calls
another node directly — routing is decided by orchestrator.py alone (deterministic, no loops).
"""

from __future__ import annotations

import logging

from app.agents.state import OrchestratorState, TraceStep
from app.ml.funding_readiness import assess_funding_readiness
from app.ml.predictor import IndustryClassifierUnavailable, predict_industry
from app.agents import student3

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


def customer_segmentation_node(state: OrchestratorState) -> dict:
    segment = student3.customer_segment(state.get("industry_prediction"), state.get("funding_assessment") or {}, customer_rfm=state.get("customer_rfm"))
    return {"customer_segment": segment, "trace": [_trace("customer_segmentation", "ok", segment["method"])]}


def recommendation_ranking_node(state: OrchestratorState) -> dict:
    actions = student3.ranked_actions(state.get("funding_assessment") or {}, state.get("industry_prediction"), state.get("customer_segment") or {})
    return {"ranked_actions": actions, "trace": [_trace("recommendation_ranking", "ok", f"{len(actions)} action(s)")]}


def innovation_node(state: OrchestratorState) -> dict:
    output = student3.innovation(state.get("industry_prediction"), state.get("funding_assessment") or {})
    return {"innovation_opportunities": output, "trace": [_trace("innovation", "ok")]}


def risk_assessment_node(state: OrchestratorState) -> dict:
    output = student3.risks(state.get("funding_assessment") or {}, state.get("industry_prediction"))
    return {"risk_assessment": output, "trace": [_trace("risk_assessment", "ok")]}


def growth_strategy_node(state: OrchestratorState) -> dict:
    output = student3.growth_strategy(state.get("customer_segment") or {}, state.get("ranked_actions") or [], state.get("industry_prediction"))
    return {"growth_strategy": output, "trace": [_trace("growth_strategy", "ok")]}


def pitch_deck_node(state: OrchestratorState) -> dict:
    output = student3.pitch_deck(state.get("startup_name", ""), state.get("startup_description", ""), state.get("industry_prediction"), state.get("funding_assessment") or {}, state.get("customer_segment") or {}, state.get("ranked_actions") or [])
    return {"pitch_deck": output, "trace": [_trace("pitch_deck", "ok")]}
