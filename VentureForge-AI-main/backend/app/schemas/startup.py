import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.ml.funding_readiness import EvidenceState, normalize_evidence_answer


class DimensionEvidence(BaseModel):
    """One funding-readiness dimension's evidence — see app.ml.funding_readiness for scoring
    semantics. Validated strictly: `severity` must be exactly 1 or 2 when `state ==
    confirmed_positive`, and must be absent for every other state. An unrecognized `state` value
    fails validation outright — this model never silently repairs a malformed *structured*
    payload. (Tolerant legacy-scalar coercion — 0/1/2/null — happens one level up, in
    `FundingAnswers._accept_legacy_or_object`, before a value ever reaches this model.)
    """

    model_config = ConfigDict(use_enum_values=True)

    state: EvidenceState = EvidenceState.NOT_SURE_YET
    severity: int | None = Field(default=None, ge=1, le=2)

    @model_validator(mode="after")
    def _severity_must_match_state(self) -> "DimensionEvidence":
        state = self.state.value if isinstance(self.state, EvidenceState) else self.state
        if state == EvidenceState.CONFIRMED_POSITIVE.value:
            if self.severity not in (1, 2):
                raise ValueError("severity must be 1 or 2 when state is 'confirmed_positive'")
        elif self.severity is not None:
            raise ValueError(f"severity must not be set when state is '{state}'")
        return self


_DIMENSION_FIELDS = (
    "problem_clarity",
    "customer_pain_evidence",
    "market_size_evidence",
    "product_maturity",
    "traction",
    "revenue_model_clarity",
    "team_completeness",
    "competitive_differentiation",
)


class FundingAnswers(BaseModel):
    """Structured funding-readiness inputs, one `DimensionEvidence` per dimension (see
    app.ml.funding_readiness.DIMENSIONS). Also accepts a legacy 0/1/2/null integer per field, for
    backward compatibility with startups submitted before the four-state evidence model existed —
    see app.ml.funding_readiness.normalize_evidence_answer for the exact legacy mapping.
    """

    problem_clarity: DimensionEvidence = Field(default_factory=DimensionEvidence)
    customer_pain_evidence: DimensionEvidence = Field(default_factory=DimensionEvidence)
    market_size_evidence: DimensionEvidence = Field(default_factory=DimensionEvidence)
    product_maturity: DimensionEvidence = Field(default_factory=DimensionEvidence)
    traction: DimensionEvidence = Field(default_factory=DimensionEvidence)
    revenue_model_clarity: DimensionEvidence = Field(default_factory=DimensionEvidence)
    team_completeness: DimensionEvidence = Field(default_factory=DimensionEvidence)
    competitive_differentiation: DimensionEvidence = Field(default_factory=DimensionEvidence)

    @field_validator(*_DIMENSION_FIELDS, mode="before")
    @classmethod
    def _accept_legacy_or_object(cls, v: object) -> object:
        """Legacy-tolerant coercion applies only to the old scalar shape (0/1/2/None, or any
        other malformed scalar, which becomes `not_sure_yet`) — see
        app.ml.funding_readiness.normalize_evidence_answer. A dict/`DimensionEvidence` input is
        the *current* structured payload and is passed through untouched, so a malformed modern
        payload (an unknown `state`, or a `confirmed_positive` with an out-of-range `severity`)
        fails strict validation on `DimensionEvidence` instead of being silently repaired.
        """
        if isinstance(v, (DimensionEvidence, dict)):
            return v
        return normalize_evidence_answer(v)


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


class CustomerRFMInput(BaseModel):
    """Optional customer-level Recency/Frequency/Monetary input for the Phase 5 (Student 3)
    trained segmentation artifact — see app.ml.segmentation. Absent entirely (not zero-filled)
    when the founder has no transaction data yet; app.agents.student3.customer_segment then
    reports segmentation as unavailable rather than fabricating a fallback segment.
    """

    recency_days: float = Field(ge=0)
    frequency: float = Field(ge=0)
    monetary: float = Field(ge=0)


class StartupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    funding_answers: FundingAnswers = Field(default_factory=FundingAnswers)
    company_metrics: CompanyMetrics = Field(default_factory=CompanyMetrics)
    revenue_assumptions: RevenueAssumptions = Field(default_factory=RevenueAssumptions)
    market_evidence: MarketEvidence = Field(default_factory=MarketEvidence)
    customer_rfm: CustomerRFMInput | None = None


class StartupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    funding_answers: dict
    company_metrics: dict
    revenue_assumptions: dict
    market_evidence: dict
    customer_rfm: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
