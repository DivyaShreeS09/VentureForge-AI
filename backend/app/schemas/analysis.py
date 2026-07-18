import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelStatusResponse(BaseModel):
    industry_classifier_loaded: bool
    industry_classifier_version: str | None
    industry_classifier_trained_at: str | None
    funding_rubric_version: str
    success_predictor_loaded: bool
    success_predictor_version: str | None
    success_predictor_trained_at: str | None
    revenue_engine_version: str
