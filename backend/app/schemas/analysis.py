import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ml.positioning_taxonomy import POSITIONING_TAXONOMY


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    startup_id: uuid.UUID
    status: str
    industry_model_version: str | None
    industry_prediction: dict[str, Any] | None
    funding_rubric_version: str | None
    funding_assessment: dict[str, Any] | None
    success_model_version: str | None
    success_prediction: dict[str, Any] | None
    revenue_engine_version: str | None
    revenue_estimate: dict[str, Any] | None
    market_intelligence: dict[str, Any] | None
    competitor_analysis: dict[str, Any] | None
    customer_personas: dict[str, Any] | None
    business_model: dict[str, Any] | None
    judge_summary: dict[str, Any] | None
    workflow_trace: list[dict[str, Any]] | None
    error_message: str | None
    # Full Mentor Orchestration phase — see app.agents.mentor_synthesis. Null only for a run whose
    # judge node itself failed, or a pre-existing analysis persisted before this phase.
    mentor_interpretation: dict[str, Any] | None = None
    # Phase 2: Idea Expansion — see app.agents.idea_expansion. Null only for a run whose mentor
    # synthesis itself did not run, or a pre-existing analysis persisted before this phase.
    idea_expansion: dict[str, Any] | None = None
    # Phase 3: Strategic Opportunity Discovery — see app.agents.strategic_opportunity. Null only
    # for a run whose mentor synthesis itself did not run, or a pre-existing analysis persisted
    # before this phase.
    strategic_opportunity: dict[str, Any] | None = None
    # Phase 5: Student 3 growth/strategy intelligence — see app.agents.student3. Null for a
    # pre-Phase-5 analysis or one whose funding_readiness node itself failed upstream.
    student3_outputs: dict[str, Any] | None = None
    # Phase C: auditable history of founder-initiated venture-positioning corrections — see
    # app.services.analysis_service.apply_industry_correction. Empty for any analysis never
    # corrected, and always present (never missing) for older, pre-Phase-C stored rows.
    positioning_correction_history: list[dict[str, Any]] = Field(default_factory=list)
    # Production-hardening phase: auditable history of founder-initiated revenue-assumption edits
    # — see app.services.analysis_service.apply_revenue_assumptions_update. Same null-normalizing
    # treatment as positioning_correction_history above, for the same reason (older stored rows).
    revenue_assumptions_history: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("positioning_correction_history", "revenue_assumptions_history", mode="before")
    @classmethod
    def _default_history_when_null(cls, value: list | None) -> list:
        # Older, pre-Phase-C stored rows (and the column's own nullable=True) may hold a real
        # NULL, not an empty list — normalize to [] rather than fail validation.
        return value if value is not None else []

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IndustryCorrectionRequest(BaseModel):
    """Founder-submitted correction to `venture_positioning` only — see
    app.agents.venture_positioning.resolve_venture_positioning's `user_override` rule (always
    wins). `model_category` (the raw trained-classifier output) is never user-editable and is
    never touched by this request.
    """

    primary_domain: str
    secondary_domains: list[str] = Field(default_factory=list)

    @field_validator("primary_domain")
    @classmethod
    def _primary_must_be_in_active_taxonomy(cls, value: str) -> str:
        if value not in POSITIONING_TAXONOMY:
            raise ValueError(f"primary_domain {value!r} is not part of the active controlled positioning taxonomy")
        return value

    @field_validator("secondary_domains")
    @classmethod
    def _secondary_must_be_in_active_taxonomy(cls, value: list[str]) -> list[str]:
        invalid = [d for d in value if d not in POSITIONING_TAXONOMY]
        if invalid:
            raise ValueError(f"secondary_domains contains domains outside the active controlled taxonomy: {invalid}")
        return value


class RevenueAssumptionsPatchRequest(BaseModel):
    """Partial (or complete) edit to the founder's revenue assumptions — see
    app.services.analysis_service.apply_revenue_assumptions_update and
    app.ml.revenue_scenario.estimate_revenue_scenario. Only fields present in the request body are
    changed (Pydantic's `model_fields_set` distinguishes "omitted" from "explicitly null"); any
    field explicitly set to `null` clears that assumption back to a suggested default rather than
    leaving a stale user-supplied value in place.

    `monthly_growth_rate_pct`'s bound (`-100` to `1000`) is the one explicitly documented place a
    negative value is permitted — a startup contracting by up to 100%/month is representable, but
    nothing more extreme; every other field must be non-negative.
    """

    price_per_customer_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    initial_customers: int | None = Field(default=None, ge=0)
    monthly_growth_rate_pct: float | None = Field(default=None, ge=-100, le=1000, allow_inf_nan=False)
    gross_margin_pct: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)


class ModelStatusResponse(BaseModel):
    industry_classifier_loaded: bool
    industry_classifier_version: str | None
    industry_classifier_trained_at: str | None
    funding_rubric_version: str
    success_predictor_loaded: bool
    success_predictor_version: str | None
    success_predictor_trained_at: str | None
    revenue_engine_version: str
