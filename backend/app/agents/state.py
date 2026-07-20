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
    # Phase 5 (Student 3) optional input — see app.schemas.startup.CustomerRFMInput. None (not
    # fabricated) when the founder submitted no transaction data.
    customer_rfm: dict[str, float] | None

    # Node outputs
    validation: dict[str, Any]
    industry_prediction: dict[str, Any] | None
    funding_assessment: dict[str, Any] | None
    # Venture-positioning outputs (Phase 0.5) — see app.agents.venture_positioning. Distinct from
    # `industry_prediction`: `model_category` is that same prediction relabeled as technical
    # evidence, `venture_positioning` is the founder-facing identity the Judge Agent's rule set
    # resolves from the controlled taxonomy + optional Gemini advisory input.
    model_category: dict[str, Any] | None
    taxonomy_candidates: list[dict[str, Any]]
    gemini_structured_recommendation: dict[str, Any] | None
    gemini_rationale: str | None
    venture_positioning: dict[str, Any] | None
    positioning_correction_rationale: str | None
    # Student 2 node outputs
    success_prediction: dict[str, Any] | None
    revenue_estimate: dict[str, Any] | None
    market_intelligence: dict[str, Any] | None
    competitor_analysis: dict[str, Any] | None
    customer_personas: dict[str, Any] | None
    business_model: dict[str, Any] | None
    evidence_check: dict[str, Any]
    judge_summary: dict[str, Any] | None
    # Full Mentor Orchestration phase — see app.agents.mentor_synthesis/mentor_reviewer. Always
    # populated (deterministic fallback) whenever judge_summary succeeded; None only if the judge
    # node itself failed upstream.
    mentor_interpretation: dict[str, Any] | None
    # Idea Expansion (Phase 2) — see app.agents.idea_expansion/idea_expansion_reviewer. Always
    # populated (deterministic fallback) whenever mentor_interpretation succeeded; None only if
    # the mentor synthesis node itself was skipped upstream.
    idea_expansion: dict[str, Any] | None
    # Strategic Opportunity Discovery (Phase 3) — see
    # app.agents.strategic_opportunity/strategic_opportunity_reviewer. Always populated
    # (deterministic fallback) whenever mentor_interpretation succeeded; None only if the mentor
    # synthesis node itself was skipped upstream.
    strategic_opportunity: dict[str, Any] | None

    # Phase 5 (Student 3) node outputs — see app.agents.student3/app.agents.nodes'
    # segment_customers_node etc. Additive; each is None/[] only if funding_readiness itself
    # failed to produce a funding_assessment upstream (never happens in practice since
    # assess_funding_readiness always returns a dict, but kept optional for type-safety).
    customer_segment: dict[str, Any] | None
    ranked_actions: list[dict[str, Any]]
    innovation_opportunities: list[dict[str, Any]]
    risk_assessment: list[dict[str, Any]]
    growth_strategy: list[dict[str, Any]]
    pitch_deck: list[dict[str, Any]]

    # Run bookkeeping. `trace` uses an additive reducer so each node's step appends rather than
    # overwriting the previous node's entry.
    trace: Annotated[list[TraceStep], operator.add]
    status: str  # "RUNNING" | "COMPLETED" | "FAILED"
    error: str | None
