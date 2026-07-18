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

    # Node outputs
    validation: dict[str, Any]
    industry_prediction: dict[str, Any] | None
    funding_assessment: dict[str, Any] | None
    market_analysis: dict[str, Any] | None
    competitor_analysis: dict[str, Any] | None
    customer_persona: dict[str, Any] | None
    business_model: dict[str, Any] | None
    evidence_check: dict[str, Any]
    judge_summary: dict[str, Any] | None

    # Run bookkeeping. `trace` uses an additive reducer so each node's step appends rather than
    # overwriting the previous node's entry.
    trace: Annotated[list[TraceStep], operator.add]
    status: str  # "RUNNING" | "COMPLETED" | "FAILED"
    error: str | None
