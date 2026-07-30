import json
import queue
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import get_db, get_session_factory
from app.schemas.analysis import AnalysisResponse, IndustryCorrectionRequest, RevenueAssumptionsPatchRequest
from app.services import analysis_events, analysis_service

router = APIRouter(prefix="/analyses", tags=["analyses"])

_TERMINAL_STATUSES = ("COMPLETED", "FAILED")


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalysisResponse:
    analysis = analysis_service.get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return AnalysisResponse.model_validate(analysis)


@router.get("/{analysis_id}/events")
def stream_analysis_events(
    analysis_id: uuid.UUID,
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
):
    """Act IV (The Forging): Server-Sent Events stream of the real Analysis row, re-emitted every
    time the background analysis thread (see app.services.analysis_service) persists a newly
    completed node — not a simulated or timed progress feed. Always emits the current real state
    first (covers a reconnect, or a run that was already finished before the client subscribed),
    then blocks on `analysis_events` until the next real update or a periodic heartbeat comment
    (a plain SSE keep-alive, never progress data) so intermediate proxies don't time out the
    connection. Closes once the analysis reaches a terminal status. `GET /analyses/{id}` above
    remains available as a plain-poll fallback and for the final full fetch.
    """
    analysis = analysis_service.get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")

    def _snapshot() -> dict:
        session = session_factory()
        try:
            row = analysis_service.get_analysis(session, analysis_id)
            return AnalysisResponse.model_validate(row).model_dump(mode="json")
        finally:
            session.close()

    def event_stream():
        payload = _snapshot()
        yield f"data: {json.dumps(payload)}\n\n"
        if payload["status"] in _TERMINAL_STATUSES:
            return

        q = analysis_events.subscribe(str(analysis_id))
        try:
            while True:
                try:
                    q.get(timeout=15)
                except queue.Empty:
                    yield ": heartbeat\n\n"
                    continue
                payload = _snapshot()
                yield f"data: {json.dumps(payload)}\n\n"
                if payload["status"] in _TERMINAL_STATUSES:
                    break
        finally:
            analysis_events.unsubscribe(str(analysis_id), q)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{analysis_id}/industry-correction", response_model=AnalysisResponse)
def correct_industry(
    analysis_id: uuid.UUID, payload: IndustryCorrectionRequest, db: Session = Depends(get_db)
) -> AnalysisResponse:
    """Founder-submitted correction to `venture_positioning` only — `primary_domain`/
    `secondary_domains` are validated against the active controlled taxonomy by
    `IndustryCorrectionRequest` itself (422 on an invalid label). Reruns the deterministic Judge
    resolution with this as a `user_override` (always wins — see
    app.agents.venture_positioning.resolve_venture_positioning) and never touches
    `model_category`. Returns the updated analysis; `positioning_correction_history` records every
    correction ever applied, oldest first.
    """
    analysis = analysis_service.apply_industry_correction(
        db, analysis_id, payload.primary_domain, payload.secondary_domains
    )
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return AnalysisResponse.model_validate(analysis)


@router.patch("/{analysis_id}/revenue-assumptions", response_model=AnalysisResponse)
def update_revenue_assumptions(
    analysis_id: uuid.UUID, payload: RevenueAssumptionsPatchRequest, db: Session = Depends(get_db)
) -> AnalysisResponse:
    """Persist a partial or complete edit to the founder's revenue assumptions. Numeric bounds
    (non-negative price/customers/margin, a documented -100..1000 growth-rate range) and
    NaN/infinite rejection are enforced by `RevenueAssumptionsPatchRequest` itself (422 on an
    invalid value). Recomputes the conservative/base/optimistic scenarios server-side and returns
    the full updated analysis; `revenue_assumptions_history` records every edit ever applied,
    oldest first. Only fields present in the request body are changed — see
    app.services.analysis_service.apply_revenue_assumptions_update.
    """
    updates = payload.model_dump(exclude_unset=True)
    analysis = analysis_service.apply_revenue_assumptions_update(db, analysis_id, updates)
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return AnalysisResponse.model_validate(analysis)
