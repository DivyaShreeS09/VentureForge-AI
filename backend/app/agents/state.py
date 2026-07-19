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
    customer_rfm: dict[str, float] | None

    # Node outputs
    validation: dict[str, Any]
    industry_prediction: dict[str, Any] | None
    funding_assessment: dict[str, Any] | None
    customer_segment: dict[str, Any] | None
    ranked_actions: list[dict[str, Any]]
    innovation_opportunities: list[dict[str, Any]]
    risk_assessment: list[dict[str, Any]]
    growth_strategy: list[dict[str, Any]]
    pitch_deck: list[dict[str, Any]]
    evidence_check: dict[str, Any]
    judge_summary: dict[str, Any] | None

    # Run bookkeeping. `trace` uses an additive reducer so each node's step appends rather than
    # overwriting the previous node's entry.
    trace: Annotated[list[TraceStep], operator.add]
    status: str  # "RUNNING" | "COMPLETED" | "FAILED"
    error: str | None
