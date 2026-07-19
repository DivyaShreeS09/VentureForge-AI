"""Strict, source-labelled contracts for the Student 3 analysis modules."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StrictModel(BaseModel):
    model_config = {"extra": "forbid"}


class CustomerSegment(StrictModel):
    segment_id: str
    segment_name: str
    fit_score: float | None = Field(default=None, ge=0, le=1)
    characteristics: list[str]
    pain_points: list[str]
    recommended_channels: list[str]
    evidence_basis: list[str]
    limitations: list[str]
    model_version: str
    method: Literal["clustering_model", "unavailable"]


class RankedAction(StrictModel):
    title: str
    priority_score: int = Field(ge=0, le=100)
    impact: Literal["low", "medium", "high"]
    effort: Literal["low", "medium", "high"]
    urgency: Literal["now", "next", "later"]
    evidence_basis: list[str]
    dependency: str
    readiness_dimension: str
    ranking_version: str


class InnovationOpportunity(StrictModel):
    category: Literal["feature", "technical", "operational", "defensibility", "ip_direction"]
    opportunity: str
    rationale: str
    validation_requirement: str
    assumptions: list[str]


class RiskItem(StrictModel):
    title: str
    category: Literal["market", "adoption", "competition", "technical", "operations", "financial", "regulatory_legal", "privacy_security", "execution_team"]
    probability_band: Literal["low", "medium", "high"]
    impact_band: Literal["low", "medium", "high"]
    severity: Literal["low", "medium", "high"]
    evidence_basis: list[str]
    mitigation: str
    early_warning_indicator: str
    assumptions: list[str]


class GrowthItem(StrictModel):
    area: Literal["validation", "acquisition", "partnership", "retention", "expansion", "experiment", "kpi"]
    recommendation: str
    rationale: str
    dependency: str
    assumptions: list[str]


class PitchSlide(StrictModel):
    title: str
    content: list[str]
    evidence_status: Literal["verified evidence", "model inference", "deterministic assessment", "assumption", "evidence required", "unknown"]


class Student3Outputs(StrictModel):
    customer_segment: CustomerSegment
    ranked_actions: list[RankedAction]
    innovation_opportunities: list[InnovationOpportunity]
    risks: list[RiskItem]
    growth_strategy: list[GrowthItem]
    pitch_deck: list[PitchSlide]
    executive_summary: list[str]
