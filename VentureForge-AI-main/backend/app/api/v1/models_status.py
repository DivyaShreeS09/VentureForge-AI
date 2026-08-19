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
        industry_classifier_test_metrics=metadata.get("test_metrics") if metadata else None,
        industry_classifier_cv_results=metadata.get("cv_results") if metadata else None,
        industry_classifier_model_card=metadata.get("model_card") if metadata else None,
        success_predictor_test_metrics=success_metadata.get("test_metrics") if success_metadata else None,
        success_predictor_cv_results=success_metadata.get("cv_results") if success_metadata else None,
        success_predictor_model_card=success_metadata.get("model_card") if success_metadata else None,
        success_predictor_disclaimer=success_metadata.get("disclaimer") if success_metadata else None,
    )
