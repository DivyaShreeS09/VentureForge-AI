import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.database.types import JSONVariant, UUIDType


class Analysis(Base):
    """One full orchestrator run for a startup: industry prediction, funding readiness, and the
    Judge Agent's synthesis of both. See docs/ARCHITECTURE.md for the orchestration flow.
    """

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    startup_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("startups.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")

    industry_model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry_prediction: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    funding_rubric_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    funding_assessment: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    # Student 2 outputs — see docs/ARCHITECTURE.md "Student 2 extension" and each producing
    # module's docstring for schema/versioning/source-attribution details.
    success_model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_prediction: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    revenue_engine_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue_estimate: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    market_intelligence: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    competitor_analysis: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    customer_personas: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    business_model: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    judge_summary: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    workflow_trace: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
