from fastapi import APIRouter

from app.ml import predictor
from app.ml.funding_readiness import RUBRIC_VERSION
from app.schemas.analysis import ModelStatusResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status", response_model=ModelStatusResponse)
def models_status() -> ModelStatusResponse:
    metadata = predictor.model_metadata()
    return ModelStatusResponse(
        industry_classifier_loaded=metadata is not None,
        industry_classifier_version=metadata.get("version") if metadata else None,
        industry_classifier_trained_at=metadata.get("trained_at") if metadata else None,
        funding_rubric_version=RUBRIC_VERSION,
    )
