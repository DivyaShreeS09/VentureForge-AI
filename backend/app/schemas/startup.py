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


class CompanyMetrics(BaseModel):
    """Optional real company/funding facts, used only by the Student 2 success-prediction model
    (app.ml.success_predictor). Every field is optional and omitted fields are imputed by the
    trained pipeline and reported back as `missing_features` — never guessed here.
    """

    total_funding_usd: float | None = Field(default=None, ge=0)
    funding_rounds: int | None = Field(default=None, ge=0)
    founded_year: int | None = Field(default=None, ge=1900, le=2100)
    country_code: str | None = Field(default=None, max_length=10)


class RevenueAssumptions(BaseModel):
    """Optional user-supplied assumptions for the deterministic revenue scenario calculator
    (app.ml.revenue_scenario) — never a trained model input. Omitted fields mean no numeric
    projection is fabricated; see that module's docstring.
    """

    price_per_customer_usd: float | None = Field(default=None, ge=0)
    initial_customers: int | None = Field(default=None, ge=0)
    monthly_growth_rate_pct: float | None = Field(default=None, ge=-100, le=1000)
    gross_margin_pct: float | None = Field(default=None, ge=0, le=100)


class MarketEvidence(BaseModel):
    """Optional user-submitted context consumed by the market intelligence, competitor analysis,
    customer persona, and business model agents (app.agents.*). Every field is optional; absent
    fields are reported as evidence gaps by those agents rather than inferred or invented.
    """

    target_market: str | None = Field(default=None, max_length=300)
    customer_type: str | None = Field(default=None, max_length=200)
    geography: str | None = Field(default=None, max_length=200)
    startup_stage: str | None = Field(default=None, max_length=100)
    known_competitors: list[str] = Field(default_factory=list)


class StartupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    funding_answers: FundingAnswers = Field(default_factory=FundingAnswers)
    company_metrics: CompanyMetrics = Field(default_factory=CompanyMetrics)
    revenue_assumptions: RevenueAssumptions = Field(default_factory=RevenueAssumptions)
    market_evidence: MarketEvidence = Field(default_factory=MarketEvidence)


class StartupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    funding_answers: dict
    company_metrics: dict
    revenue_assumptions: dict
    market_evidence: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
