"""Typed orchestrator state shared by every node in backend/app/agents/orchestrator.py."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class TraceStep(TypedDict):
    node: str
    status: str  # "ok" | "error" | "skipped"
    detail: str | None


class OrchestratorState(TypedDict, total=False):
    # Inputs
    startup_name: str
    startup_description: str
    funding_answers: dict[str, int | None]
    # Student 2 optional inputs — see app.schemas.startup.CompanyMetrics/RevenueAssumptions/
    # MarketEvidence. Always present as {} (not fabricated) when the user submitted nothing.
    company_metrics: dict[str, Any]
    revenue_assumptions: dict[str, Any]
    market_evidence: dict[str, Any]

    # Node outputs
    validation: dict[str, Any]
    industry_prediction: dict[str, Any] | None
    funding_assessment: dict[str, Any] | None
    # Student 2 node outputs
    success_prediction: dict[str, Any] | None
    revenue_estimate: dict[str, Any] | None
    market_intelligence: dict[str, Any] | None
    competitor_analysis: dict[str, Any] | None
    customer_personas: dict[str, Any] | None
    business_model: dict[str, Any] | None
    evidence_check: dict[str, Any]
    judge_summary: dict[str, Any] | None

    # Run bookkeeping. `trace` uses an additive reducer so each node's step appends rather than
    # overwriting the previous node's entry.
    trace: Annotated[list[TraceStep], operator.add]
    status: str  # "RUNNING" | "COMPLETED" | "FAILED"
    error: str | None
