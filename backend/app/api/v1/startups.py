import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import get_db, get_session_factory
from app.schemas.analysis import AnalysisResponse
from app.schemas.startup import StartupCreateRequest, StartupResponse
from app.services import analysis_service

router = APIRouter(prefix="/startups", tags=["startups"])


@router.post("", response_model=StartupResponse, status_code=status.HTTP_201_CREATED)
def create_startup(payload: StartupCreateRequest, db: Session = Depends(get_db)) -> StartupResponse:
    startup = analysis_service.create_startup(db, payload)
    return StartupResponse.model_validate(startup)


@router.get("/{startup_id}", response_model=StartupResponse)
def get_startup(startup_id: uuid.UUID, db: Session = Depends(get_db)) -> StartupResponse:
    startup = analysis_service.get_startup(db, startup_id)
    if startup is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Startup not found")
    return StartupResponse.model_validate(startup)


@router.post("/{startup_id}/analyze", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def analyze_startup(
    startup_id: uuid.UUID,
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
) -> AnalysisResponse:
    """Act IV (The Forging): returns immediately once the analysis row is created (status
    RUNNING) — the real orchestrator run continues in the background and reports genuine,
    incremental progress. See `GET /analyses/{id}/events` (SSE) and `GET /analyses/{id}` (poll
    fallback / final fetch) in app/api/v1/analyses.py.
    """
    startup = analysis_service.get_startup(db, startup_id)
    if startup is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Startup not found")
    analysis = analysis_service.start_analysis_for_startup(db, startup, session_factory)
    return AnalysisResponse.model_validate(analysis)
