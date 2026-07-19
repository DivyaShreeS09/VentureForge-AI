"""Business logic for creating startups and running/persisting their analysis pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.orchestrator import run_pipeline
from app.agents.state import OrchestratorState
from app.models.analysis import Analysis
from app.models.startup import Startup
from app.schemas.startup import StartupCreateRequest
from app.schemas.student3 import Student3Outputs


def create_startup(db: Session, payload: StartupCreateRequest) -> Startup:
    now = datetime.now(timezone.utc)
    startup = Startup(
        name=payload.name,
        description=payload.description,
        funding_answers=payload.funding_answers.model_dump(),
        customer_rfm=payload.customer_rfm.model_dump() if payload.customer_rfm else None,
        created_at=now,
        updated_at=now,
    )
    db.add(startup)
    db.commit()
    db.refresh(startup)
    return startup


def get_startup(db: Session, startup_id: uuid.UUID) -> Startup | None:
    return db.get(Startup, startup_id)


def get_analysis(db: Session, analysis_id: uuid.UUID) -> Analysis | None:
    return db.get(Analysis, analysis_id)


def run_analysis_for_startup(db: Session, startup: Startup) -> Analysis:
    """Run the orchestrator synchronously and persist the result as a new Analysis row."""
    now = datetime.now(timezone.utc)
    analysis = Analysis(startup_id=startup.id, status="PENDING", created_at=now, updated_at=now)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    def persist(state: OrchestratorState) -> None:
        industry = state.get("industry_prediction")
        funding = state.get("funding_assessment")
        analysis.status = state.get("status", "FAILED")
        analysis.industry_prediction = industry
        analysis.industry_model_version = industry.get("model_version") if industry else None
        analysis.funding_assessment = funding
        analysis.funding_rubric_version = funding.get("rubric_version") if funding else None
        if state.get("status") == "COMPLETED":
            analysis.student3_outputs = Student3Outputs(
                customer_segment=state.get("customer_segment"),
                ranked_actions=state.get("ranked_actions") or [],
                innovation_opportunities=state.get("innovation_opportunities") or [],
                risks=state.get("risk_assessment") or [],
                growth_strategy=state.get("growth_strategy") or [],
                pitch_deck=state.get("pitch_deck") or [],
                executive_summary=[state.get("judge_summary", {}).get("overall_assessment", "")],
            ).model_dump()
        else:
            analysis.student3_outputs = None
        analysis.judge_summary = state.get("judge_summary")
        analysis.workflow_trace = state.get("trace")
        analysis.error_message = state.get("error")
        analysis.updated_at = datetime.now(timezone.utc)
        db.add(analysis)
        db.commit()

    run_pipeline(
        startup_name=startup.name,
        startup_description=startup.description,
        funding_answers=startup.funding_answers,
        customer_rfm=startup.customer_rfm,
        persist_fn=persist,
    )
    db.refresh(analysis)
    return analysis
