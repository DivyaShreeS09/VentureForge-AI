"""Orchestrator node functions. Each is a plain, independently-testable function: takes the
current state, returns the keys it updates (LangGraph merges these into state). No node calls
another node directly — routing is decided by orchestrator.py alone (deterministic, no loops).
"""

from __future__ import annotations

import logging

from app.agents.business_model_agent import generate_business_model
from app.agents.competitor_agent import generate_competitor_analysis
from app.agents.customer_persona_agent import generate_customer_persona
from app.agents.market_agent import generate_market_analysis
from app.agents.state import OrchestratorState, TraceStep
from app.ml.funding_readiness import assess_funding_readiness
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
    result = estimate_revenue_scenario(
        price_per_customer_usd=assumptions.get("price_per_customer_usd"),
        initial_customers=assumptions.get("initial_customers"),
        monthly_growth_rate_pct=assumptions.get("monthly_growth_rate_pct"),
        gross_margin_pct=assumptions.get("gross_margin_pct"),
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
    result = generate_competitor_analysis(
        known_competitors=market_evidence.get("known_competitors") or [],
        industry_prediction=state.get("industry_prediction"),
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
