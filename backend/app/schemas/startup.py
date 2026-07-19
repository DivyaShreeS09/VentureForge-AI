import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FundingAnswers(BaseModel):
    """Structured funding-readiness inputs. Each field is 0 (no evidence), 1 (some evidence), 2
    (strong evidence), or omitted if unknown — see app.ml.funding_readiness.DIMENSIONS.
    """

    problem_clarity: int | None = Field(default=None, ge=0, le=2)
    customer_pain_evidence: int | None = Field(default=None, ge=0, le=2)
    market_size_evidence: int | None = Field(default=None, ge=0, le=2)
    product_maturity: int | None = Field(default=None, ge=0, le=2)
    traction: int | None = Field(default=None, ge=0, le=2)
    revenue_model_clarity: int | None = Field(default=None, ge=0, le=2)
    team_completeness: int | None = Field(default=None, ge=0, le=2)
    competitive_differentiation: int | None = Field(default=None, ge=0, le=2)


class CustomerRFMInput(BaseModel):
    recency_days: float = Field(ge=0)
    frequency: float = Field(ge=0)
    monetary: float = Field(ge=0)


class StartupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    funding_answers: FundingAnswers = Field(default_factory=FundingAnswers)
    customer_rfm: CustomerRFMInput | None = None


class StartupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    funding_answers: dict
    customer_rfm: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
