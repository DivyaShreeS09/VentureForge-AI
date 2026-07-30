"""Versioned MentorInterpretation schema (Full Mentor Orchestration phase).

The single coherent, founder-facing mentor result — replacing a bare collection of agent reports.
Produced by app.agents.mentor_synthesis.build_deterministic_mentor (always, fully deterministic)
and always passed through app.agents.mentor_reviewer.review_mentor_safely, which appends
`mentor_advice_items` (Gemini-authored, tagged, schema/safety-validated strategic advice — see that
module) without ever touching any other field here. Every instance validates against this exact
schema — the frontend and every test can rely on one shape regardless of whether Gemini contributed
advice or not.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MENTOR_SCHEMA_VERSION = "v1"


class IdeaUnderstanding(BaseModel):
    summary: str
    target_user: str
    problem: str
    proposed_solution: str
    business_context: str


class FeatureGapAnalysis(BaseModel):
    present_capabilities: list[dict] = Field(default_factory=list)
    recommended_capabilities: list[dict] = Field(default_factory=list)
    premature_capabilities: list[dict] = Field(default_factory=list)
    not_relevant_capabilities: list[dict] = Field(default_factory=list)


class MvpRecommendation(BaseModel):
    target_user: str
    single_core_problem: str
    minimum_workflow: str
    included_capabilities: list[str] = Field(default_factory=list)
    excluded_for_now: list[str] = Field(default_factory=list)
    success_metric: str
    pilot_environment: str
    reasons: list[str] = Field(default_factory=list)


class ValidationAction(BaseModel):
    priority: int
    question_to_answer: str
    method: str
    target_participants: str
    success_criterion: str
    source_gap: str
    build_dependency: str


class RoadmapPeriod(BaseModel):
    period: Literal["days_1_30", "days_31_60", "days_61_90"]
    focus: str
    activities: list[str] = Field(default_factory=list)
    rationale: str


class MentorVerdict(BaseModel):
    readiness_level: str
    concise_verdict: str
    strongest_signal: str
    biggest_risk: str
    immediate_priority: str


class EvidenceAndUncertainty(BaseModel):
    model_category_caveat: str
    historical_pattern_signal_caveat: str
    low_confidence_flags: list[str] = Field(default_factory=list)
    user_supplied_vs_suggested_summary: str
    unresolved_questions: list[str] = Field(default_factory=list)


class MentorInterpretation(BaseModel):
    mentor_schema_version: str = MENTOR_SCHEMA_VERSION
    # Always "deterministic" — every field below (other than mentor_advice_items) is fully
    # produced by app.agents.mentor_synthesis with no network dependency. Gemini's contribution,
    # if any, lives entirely in mentor_advice_items and never changes this value or any other field
    # (see app.agents.mentor_reviewer).
    source: Literal["deterministic", "gemini"]
    # Gemini-authored, tagged strategic advice (Product Intelligence Sprint) — see
    # app.agents.mentor_reviewer.review_mentor_safely and app.ai.schemas.GeminiMentorAdviceItem.
    # Empty when Gemini is unconfigured/unavailable/every item failed a safety check; every present
    # item carries its own `domain` and `category` (never "evidence") so a rendering surface can
    # show what kind of claim it is. Never overwrites or contradicts any other field here.
    mentor_advice_items: list[dict] = Field(default_factory=list)

    idea_understanding: IdeaUnderstanding
    # A short mentor-facing narrative referencing the Judge Agent's already-decided
    # venture_positioning (see app.agents.venture_positioning) — never a second, competing
    # decision; this field only ever restates what the Judge already resolved.
    venture_positioning: str
    # Deprecated, backward-compatibility only (Phase 1 correction) — no new code reads these raw
    # string lists. `founder_guidance_items` below is the structured replacement every new
    # consumer (frontend, prioritization) must use instead.
    strengths: list[str] = Field(default_factory=list)
    real_weaknesses: list[str] = Field(default_factory=list)
    suggested_possibilities: list[dict] = Field(default_factory=list)
    # The single structured, coached list backing the founder-facing opportunities/validation/
    # action-list rendering — one deterministic priority order shared by every consumer (see
    # app.agents.founder_guidance). Merges funding-readiness-dimension items (from judge_summary)
    # with capability-library-derived items (future_enhancement/improvement_opportunity).
    founder_guidance_items: list[dict] = Field(default_factory=list)
    feature_gap_analysis: FeatureGapAnalysis
    customer_and_market: str
    business_model: str
    competitor_landscape: str
    revenue_scenarios: str
    # Product Intelligence Sprint (Phase 3) — see app.agents.pricing_intelligence. Always a complete
    # dict: a currency (INR/USD/USD-INR when genuinely mixed), a detected-or-assumed target market,
    # and either a single recommended_price_per_customer (only when confident) or a
    # recommended_price_range (otherwise) — never both, never neither.
    pricing_intelligence: dict
    # Product Intelligence Sprint (Phase 4) — see app.agents.go_to_market_intelligence. Answers who
    # to approach first, where to find the first ~20 customers, the early-adopter profile, outreach
    # strategy, distribution channels, sales motion, and validation/expansion roadmaps.
    go_to_market_intelligence: dict
    # Product Intelligence Sprint (Phase 5) — see app.agents.feature_intelligence. 8 concrete,
    # category-flavored differentiation/monetization feature ideas (AI feature, automation,
    # analytics, integrations, premium tier, enterprise feature, future roadmap, monetization),
    # each with an explicit reason — never a bare "needs differentiation" statement.
    feature_intelligence: dict
    # Product Intelligence Sprint (Phase 6) — see app.agents.competitor_intelligence.
    # Category-level customer-alternative/switching-behavior/switching-friction/how-to-win
    # analysis — never a claim about a specific real company's actual product or position.
    competitor_intelligence: dict
    # Product Intelligence Sprint (Phase 7) — see app.agents.founder_report. A professional,
    # investor/founder-quality report composed entirely from the sections above: Executive
    # Summary, Startup Snapshot, Problem/Customer/Market analysis, Pricing Strategy, GTM Strategy,
    # Competitive Landscape, Product Roadmap, AI Feature Suggestions, Risk/Opportunity Assessment,
    # Funding Readiness, 90-Day Action Plan, and Final Mentor Verdict — every item explicitly
    # tagged evidence/inference/ai_recommendation/market_assumption/experiment_suggestion.
    founder_report: dict
    mvp_recommendation: MvpRecommendation
    validation_plan: list[ValidationAction] = Field(default_factory=list)
    roadmap_30_60_90: list[RoadmapPeriod] = Field(default_factory=list)
    top_next_actions: list[str] = Field(default_factory=list)
    mentor_verdict: MentorVerdict
    evidence_and_uncertainty: EvidenceAndUncertainty
    # Every section attributed to its source (deterministic component, trained ML model,
    # user-submitted evidence, or Gemini) — mirrors the pattern already established in
    # app.agents.judge.synthesize's own `source_attribution`.
    source_attribution: dict[str, str] = Field(default_factory=dict)
