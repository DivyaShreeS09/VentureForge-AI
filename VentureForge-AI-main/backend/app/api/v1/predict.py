from fastapi import APIRouter

from app.agents.nodes import MIN_DESCRIPTION_LENGTH
from app.ml.positioning_taxonomy import extract_deployment_sectors
from app.ml.predictor import IndustryClassifierUnavailable, predict_industry
from app.schemas.discovery_preview import CustomerHint, IndustryPreviewRequest, IndustryPreviewResponse

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("/industry", response_model=IndustryPreviewResponse)
def preview_industry(payload: IndustryPreviewRequest) -> IndustryPreviewResponse:
    """Thin, read-only preview for the frontend's Discovery flow — reuses the exact same
    `predict_industry` call and `extract_deployment_sectors` call the real orchestrator runs
    during Forging (see app.agents.nodes.industry_classification_node / score_taxonomy). No
    Startup row is created or persisted here; this never touches the database.

    `available: false` (never a 5xx) covers both an untrained classifier artifact and a
    description too short for the orchestrator to accept — the same `MIN_DESCRIPTION_LENGTH`
    gate `input_validation_node` already enforces, reused rather than re-invented here, so the
    live preview never disagrees with what Forging will actually accept.
    """
    description = payload.description.strip()
    if len(description) < MIN_DESCRIPTION_LENGTH:
        return IndustryPreviewResponse(available=False)

    try:
        result = predict_industry(payload.name, description)
    except IndustryClassifierUnavailable:
        return IndustryPreviewResponse(available=False)

    sectors = extract_deployment_sectors(description)
    detected_keywords = sorted({keyword for sector in sectors for keyword in sector["matched_text"]})

    return IndustryPreviewResponse(
        available=True,
        predicted_industry=result["predicted_industry"],
        confidence=result["confidence"],
        is_uncertain=result["is_uncertain"],
        uncertainty_reasons=result["uncertainty_reasons"],
        secondary_industry=result["secondary_industry"],
        secondary_confidence=result["secondary_confidence"],
        model_version=result["model_version"],
        customer_hints=[CustomerHint(**sector) for sector in sectors],
        detected_keywords=detected_keywords,
    )
