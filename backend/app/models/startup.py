import uuid
from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.database.types import JSONVariant, UUIDType


class Startup(Base):
    __tablename__ = "startups"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Raw 0/1/2 funding-readiness dimension answers submitted by the user (see
    # app.ml.funding_readiness.DIMENSIONS for the schema of this payload).
    funding_answers: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    # Optional Student 2 inputs — see app.schemas.startup.CompanyMetrics/RevenueAssumptions/
    # MarketEvidence. All default to {} (empty, not fabricated) rather than null so downstream
    # code can always call .get() without a None check.
    company_metrics: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    revenue_assumptions: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    market_evidence: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
