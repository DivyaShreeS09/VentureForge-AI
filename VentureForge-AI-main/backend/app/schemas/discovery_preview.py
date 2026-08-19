"""Response contract for `POST /api/v1/predict/industry` — a thin, read-only preview used only by
the frontend's Discovery flow (Act II, "Who It's For") to reflect a live industry/customer signal
back to the founder while they're still typing, before a Startup is ever created or analyzed.

This is not a second prediction path: every field below is copied or trivially reshaped from the
exact same `app.ml.predictor.predict_industry` call and `app.ml.positioning_taxonomy.
extract_deployment_sectors` call the real orchestrator (`app.agents.nodes.industry_classification_
node` / `score_taxonomy`) already uses during Forging. No new model, no new heuristic, no new
confidence calculation is introduced here — see `app.api.v1.predict` for the route itself.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class IndustryPreviewRequest(BaseModel):
    name: str = Field(default="", max_length=200)
    description: str = Field(min_length=1, max_length=5000)


class CustomerHint(BaseModel):
    """One deployment-sector match from `positioning_taxonomy.extract_deployment_sectors` —
    e.g. {"sector": "Hotels", "matched_text": ["hotel"]}. Deterministic keyword extraction, not a
    model prediction — presented to the founder as "who this might be for," never as a confidence
    score."""

    sector: str
    matched_text: list[str]


class IndustryPreviewResponse(BaseModel):
    available: bool
    # Populated only when `available` is true — the classifier artifact may not be trained in
    # every environment (see IndustryClassifierUnavailable), and this response must say so plainly
    # rather than fabricate a prediction.
    predicted_industry: str | None = None
    confidence: float | None = None
    is_uncertain: bool | None = None
    uncertainty_reasons: list[str] = Field(default_factory=list)
    secondary_industry: str | None = None
    secondary_confidence: float | None = None
    model_version: str | None = None
    customer_hints: list[CustomerHint] = Field(default_factory=list)
    detected_keywords: list[str] = Field(default_factory=list)
