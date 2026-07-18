from fastapi import APIRouter

from app.ml import predictor, success_predictor
from app.ml.funding_readiness import RUBRIC_VERSION
from app.ml.revenue_scenario import SCENARIO_ENGINE_VERSION
from app.schemas.analysis import ModelStatusResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status", response_model=ModelStatusResponse)
def models_status() -> ModelStatusResponse:
    metadata = predictor.model_metadata()
    success_metadata = success_predictor.model_metadata()
    return ModelStatusResponse(
        industry_classifier_loaded=metadata is not None,
        industry_classifier_version=metadata.get("version") if metadata else None,
        industry_classifier_trained_at=metadata.get("trained_at") if metadata else None,
        funding_rubric_version=RUBRIC_VERSION,
        success_predictor_loaded=success_metadata is not None,
        success_predictor_version=success_metadata.get("version") if success_metadata else None,
        success_predictor_trained_at=success_metadata.get("trained_at") if success_metadata else None,
        revenue_engine_version=SCENARIO_ENGINE_VERSION,
    )
