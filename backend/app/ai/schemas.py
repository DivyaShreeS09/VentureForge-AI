"""Pydantic contracts for the optional LLM narrative layer.

`NarrativeContext` is what the deterministic pipeline sends to a provider — it contains only
already-computed facts (predictions, scores, user-provided answers), never raw instructions.
`NarrativeEnhancement` is what a provider must return; every field is length- and count-bounded so
a malformed or oversized response is rejected by validation rather than rendered as-is, and so the
narrative can never smuggle in something the size of a second industry classification or score.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.ml.positioning_taxonomy import POSITIONING_TAXONOMY

MAX_SUMMARY_LENGTH = 600
MAX_LIST_ITEMS = 6
MAX_ITEM_LENGTH = 220

_ALLOWED_POSITIONING_DOMAINS = frozenset(POSITIONING_TAXONOMY.keys())
MAX_RATIONALE_LENGTH = 600


class NarrativeContext(BaseModel):
    """Read-only facts passed to an LLM provider. No user free-text field here is ever treated as
    an instruction — see backend/app/ai/guardrails.py for how it is delimited in the prompt."""

    startup_name: str
    startup_description: str
    predicted_industry: str
    industry_confidence: float
    industry_is_uncertain: bool
    funding_score: float
    funding_level: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


def _bounded_list(items: list[str]) -> list[str]:
    return [item.strip()[:MAX_ITEM_LENGTH] for item in items[:MAX_LIST_ITEMS] if item and item.strip()]


class NarrativeEnhancement(BaseModel):
    """The only thing an LLM provider is allowed to produce: supplementary narrative text. It has
    no field for industry, confidence, or funding score — there is nothing for a provider to
    override even if it tried, because those fields do not exist in this schema."""

    executive_summary: str = Field(max_length=MAX_SUMMARY_LENGTH)
    strategic_observations: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @field_validator("strategic_observations", "strengths", "weaknesses", "recommendations")
    @classmethod
    def _bound_lists(cls, value: list[str]) -> list[str]:
        return _bounded_list(value)

    @field_validator("executive_summary")
    @classmethod
    def _strip_summary(cls, value: str) -> str:
        return value.strip()


class PositioningReviewContext(BaseModel):
    """Read-only facts sent to the Gemini positioning reviewer (Phase 0.5). Gemini never sees the
    Judge's decision rules — it only ever proposes a structured recommendation from this fixed
    context; see app.agents.venture_positioning for how (little) weight the Judge gives it.
    """

    startup_description: str
    model_category_label: str
    model_category_confidence: float
    model_category_is_uncertain: bool
    taxonomy_candidate_domains: list[str] = Field(default_factory=list)


class GeminiPositioningRecommendation(BaseModel):
    """The *only* shape a positioning reviewer response may take: a primary/secondary
    recommendation restricted to the controlled taxonomy, a confidence score, and a free-text
    rationale. `rationale` is carried through purely as a human-readable explanation — see
    app.agents.venture_positioning.resolve_venture_positioning, which never parses or scores it;
    only `recommended_primary_domain`, `recommended_secondary_domains`, and `confidence` (all
    closed-enum/typed fields) are ever read by the Judge's decision rules.
    """

    recommended_primary_domain: str
    recommended_secondary_domains: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(default="", max_length=MAX_RATIONALE_LENGTH)

    @field_validator("recommended_primary_domain")
    @classmethod
    def _primary_must_be_in_controlled_taxonomy(cls, value: str) -> str:
        if value not in _ALLOWED_POSITIONING_DOMAINS:
            raise ValueError(
                f"recommended_primary_domain {value!r} is not part of the controlled positioning taxonomy"
            )
        return value

    @field_validator("recommended_secondary_domains")
    @classmethod
    def _secondary_must_be_in_controlled_taxonomy(cls, value: list[str]) -> list[str]:
        invalid = [d for d in value if d not in _ALLOWED_POSITIONING_DOMAINS]
        if invalid:
            raise ValueError(
                f"recommended_secondary_domains contains domains outside the controlled taxonomy: {invalid}"
            )
        return value[:3]

    @field_validator("rationale")
    @classmethod
    def _strip_rationale(cls, value: str) -> str:
        return value.strip()


class CompetitorPossibilitiesContext(BaseModel):
    """Read-only facts sent to the Gemini competitor-possibilities reviewer (Phase B)."""

    startup_description: str
    model_category_label: str
    venture_positioning_primary_domain: str | None = None


MAX_COMPETITOR_POSSIBILITIES = 5
MAX_CATEGORY_LENGTH = 120
MAX_REASON_LENGTH = 240
MAX_POSSIBILITY_LENGTH = MAX_CATEGORY_LENGTH  # kept for any external caller still importing this


def _looks_like_named_company(phrase: str) -> bool:
    """Heuristic-only proper-noun detector: a legitimate category phrase reads like "food delivery
    apps" or "general point-of-sale software" — plain, lowercase, generic — never "Uber Eats" or
    "Toast POS". Any Title-Case word (first letter uppercase, not a short all-caps acronym like
    "POS"/"SaaS") anywhere in the phrase, including the first word, is treated as a likely brand
    name and the whole phrase is dropped. Retained as defense-in-depth alongside the structural
    checks below (URL/email/corporate-suffix detection) — none of these individually is a
    guarantee, but a Gemini response has to evade all of them simultaneously to smuggle in an
    unsourced proper-noun company claim into `unverified_possibilities` (see
    app.agents.competitor_agent).
    """
    for word in phrase.split():
        letters_only = "".join(c for c in word if c.isalpha())
        if not letters_only:
            continue
        if letters_only.isupper():
            continue  # a short all-caps acronym (e.g. "POS", "SaaS") is not itself a brand name
        if letters_only[0].isupper():
            return True
    return False


_URL_OR_DOMAIN_PATTERN = re.compile(
    r"https?://|www\.|\b[a-z0-9-]+\.(com|io|ai|net|org|co|app|xyz|biz|dev)\b", re.IGNORECASE
)
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
_CORPORATE_SUFFIX_PATTERN = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c\.|ltd|plc|pvt\.?\s*ltd|corp|corporation|co\.|gmbh|s\.a\.)\b",
    re.IGNORECASE,
)


def _fails_structural_safety_checks(text: str) -> bool:
    """Reject a candidate category/reason string that contains a URL, a domain-like token, an
    email address, a corporate legal suffix, or (as defense-in-depth) something that reads like a
    proper-noun brand name. Any one of these is independent grounds for rejection — this is a
    disjunction of cheap, explainable structural checks, not a single fragile classifier."""
    return bool(
        _URL_OR_DOMAIN_PATTERN.search(text)
        or _EMAIL_PATTERN.search(text)
        or _CORPORATE_SUFFIX_PATTERN.search(text)
        or _looks_like_named_company(text)
    )


class CompetitorSolutionType(str, Enum):
    """Closed enum of solution shapes a category-level competitor possibility may take — Gemini
    must pick one of these rather than free-text, so this field can never itself smuggle in a
    company name."""

    SOFTWARE_PLATFORM = "software_platform"
    MARKETPLACE = "marketplace"
    MANUAL_PROCESS_TOOL = "manual_process_tool"
    SERVICE_PROVIDER = "service_provider"
    OTHER_CATEGORY = "other_category"


class GeminiCompetitorPossibility(BaseModel):
    """One typed, category-level competitor possibility. There is deliberately no field here for a
    company/brand/product name anywhere in this schema — Gemini has nothing to put a specific
    business's name into even if it tried; `category` and `reason` are still checked against
    `_fails_structural_safety_checks` (see `GeminiCompetitorPossibilities`) since free text could
    still smuggle a name or an unsupported specific-business claim into either field.
    """

    category: str = Field(max_length=MAX_CATEGORY_LENGTH)
    solution_type: CompetitorSolutionType
    reason: str = Field(max_length=MAX_REASON_LENGTH)
    source: Literal["ai_suggested_category"] = "ai_suggested_category"

    @field_validator("category", "reason")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


def _validate_one_possibility(raw: object) -> GeminiCompetitorPossibility | None:
    """Attempt to construct and safety-check a single possibility item. Returns None (never
    raises) for anything invalid — malformed shape, empty text, or a failed structural safety
    check — so the caller can discard just this one item and keep the rest of the list."""
    if not isinstance(raw, dict):
        return None
    try:
        item = GeminiCompetitorPossibility.model_validate(raw)
    except Exception:
        return None
    if not item.category or not item.reason:
        return None
    if _fails_structural_safety_checks(item.category) or _fails_structural_safety_checks(item.reason):
        return None
    return item


class MentorContext(BaseModel):
    """Structured, source-attributed facts sent to the Gemini mentor advisor (Full Mentor
    Orchestration phase) — every fact here was already computed deterministically by
    app.agents.mentor_synthesis.build_deterministic_mentor. Gemini's job (Product Intelligence
    Sprint: "Gemini should think, not rewrite") is to ENRICH this baseline with new, clearly-tagged
    strategic advice (see GeminiMentorAdvice below) — never to rephrase, replace, or override any
    field already decided here, and never to assert a new fact, competitor, number, or decision
    that isn't already present in this context. `startup_description` is DATA to analyze (see
    app.ai.guardrails' prompt-injection framing), never an instruction.
    """

    startup_name: str
    startup_description: str
    venture_positioning_text: str
    strengths: list[str] = Field(default_factory=list)
    real_weaknesses: list[str] = Field(default_factory=list)
    funding_level: str
    customer_and_market_facts: str
    business_model_facts: str
    competitor_landscape_facts: str
    revenue_scenarios_facts: str
    mvp_single_core_problem_facts: str
    mvp_minimum_workflow_facts: str
    mvp_success_metric_facts: str
    mvp_pilot_environment_facts: str
    idea_understanding_facts: dict


class MentorAdviceCategory(str, Enum):
    """Every sentence Gemini contributes to the mentor advice list must self-declare which of
    these five categories it is — this is the structural backbone of the "Gemini should think, not
    rewrite" redesign. `EVIDENCE` is deliberately impossible for Gemini to claim (see the
    validator below): evidence is, by definition, something already established in the
    deterministic baseline or the founder's own description, never something Gemini asserts about
    itself.
    """

    EVIDENCE = "evidence"
    INFERENCE = "inference"
    AI_RECOMMENDATION = "ai_recommendation"
    MARKET_ASSUMPTION = "market_assumption"
    EXPERIMENT_SUGGESTION = "experiment_suggestion"


class MentorAdviceDomain(str, Enum):
    """The 13 advice domains Gemini may reason about — deliberately every one is *advice*
    (a suggestion, a rationale, a strategy) and none is a *decision* (positioning, funding
    readiness, ranking) — those stay exclusively deterministic/Judge-owned."""

    FEATURE_IDEA = "feature_idea"
    DIFFERENTIATION = "differentiation"
    GO_TO_MARKET = "go_to_market"
    PILOT_STRATEGY = "pilot_strategy"
    PRICING_RATIONALE = "pricing_rationale"
    MARKETING = "marketing"
    CUSTOMER_ACQUISITION = "customer_acquisition"
    FUNDRAISING_GUIDANCE = "fundraising_guidance"
    ROADMAP = "roadmap"
    EXECUTION_ADVICE = "execution_advice"
    RISK_MITIGATION = "risk_mitigation"
    ALTERNATIVE_BUSINESS_MODEL = "alternative_business_model"
    GROWTH_EXPERIMENT = "growth_experiment"


MAX_MENTOR_ADVICE_ITEMS = 10
MAX_MENTOR_ADVICE_TEXT_LENGTH = 320

# Defense-in-depth against Gemini asserting external research it cannot actually have performed
# (the mandate's "may not invent... citations... research results"). Not a guarantee on its own —
# paired with the number/proper-noun guards in app.agents.mentor_reviewer, matching the same
# "disjunction of cheap, explainable structural checks" philosophy already used for competitor
# possibilities (see _fails_structural_safety_checks above).
_CITATION_CLAIM_PATTERN = re.compile(
    r"\b(according to|studies? show|research (shows|indicates|suggests)|cited|source:|data from|"
    r"survey (shows|found)|report(s)? (show|indicate))\b",
    re.IGNORECASE,
)


class GeminiMentorAdviceItem(BaseModel):
    """One tagged, bounded piece of advice. `domain` says what kind of advice it is; `category`
    says what epistemic status it has — the two are orthogonal and both mandatory, so a rendering
    surface can never show advice without disclosing its own certainty level."""

    domain: MentorAdviceDomain
    category: MentorAdviceCategory
    text: str = Field(max_length=MAX_MENTOR_ADVICE_TEXT_LENGTH)

    @field_validator("text")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("category")
    @classmethod
    def _gemini_may_never_self_certify_as_evidence(cls, value: "MentorAdviceCategory") -> "MentorAdviceCategory":
        if value == MentorAdviceCategory.EVIDENCE:
            raise ValueError(
                "Gemini-authored mentor advice may never tag itself 'evidence' — evidence is "
                "reserved for facts already established in the deterministic baseline or the "
                "founder's own description, never a claim Gemini makes about itself."
            )
        return value


class GeminiMentorAdvice(BaseModel):
    """The *only* shape a Gemini mentor-advice response may take: a bounded list of tagged advice
    items. There is no field here for venture_positioning, funding readiness, idea_understanding,
    or any other deterministic/Judge-owned value — Gemini enriches the mentor report, it never
    overwrites it (see app.agents.mentor_reviewer.enrich_mentor_safely for the additional
    per-item safety checks — no unsupported numeric claims, no unattested proper nouns, no
    citation-style research claims — applied before any item is used)."""

    advice: list[GeminiMentorAdviceItem] = Field(default_factory=list)

    @field_validator("advice", mode="before")
    @classmethod
    def _bound_items(cls, value: object) -> list:
        if not isinstance(value, list):
            return []
        return value[:MAX_MENTOR_ADVICE_ITEMS]


MAX_IDEA_EXPANSION_ITEMS = 4
MAX_IDEA_TITLE_LENGTH = 120
MAX_IDEA_REASON_LENGTH = 280


class GeminiIdeaConfidenceTier(str, Enum):
    """Gemini's Idea Expansion items may only ever claim one of these two tiers — there is no enum
    value for "confirmed_from_evidence" here, so Gemini has nothing to put such a claim into even
    if it tried. That tier is reserved for items app.agents.idea_expansion derives directly from
    this venture's own already-computed deterministic data (see app.agents.idea_expansion_reviewer
    for how the two sources are merged)."""

    REASONABLE_HYPOTHESIS = "reasonable_hypothesis"
    SPECULATIVE_FUTURE_OPPORTUNITY = "speculative_future_opportunity"


class IdeaExpansionContext(BaseModel):
    """Read-only facts sent to the Gemini Idea Expansion reviewer (Phase 2). Every fact here was
    already computed deterministically — Gemini's job is to propose additional, clearly-tiered
    possibilities, never to alter venture positioning, funding readiness, or any Judge-owned field.
    """

    startup_name: str
    startup_description: str
    primary_domain: str | None = None
    secondary_domains: list[str] = Field(default_factory=list)
    deployment_sectors: list[str] = Field(default_factory=list)
    funding_level: str
    present_capability_labels: list[str] = Field(default_factory=list)
    recommended_capability_labels: list[str] = Field(default_factory=list)
    mvp_single_core_problem: str = ""


class GeminiIdeaExpansionItem(BaseModel):
    title: str = Field(max_length=MAX_IDEA_TITLE_LENGTH)
    reason: str = Field(max_length=MAX_IDEA_REASON_LENGTH)
    confidence_tier: GeminiIdeaConfidenceTier

    @field_validator("title", "reason")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


def _bounded_idea_items(value: object) -> list:
    if not isinstance(value, list):
        return []
    return value[:MAX_IDEA_EXPANSION_ITEMS]


class GeminiIdeaExpansion(BaseModel):
    """The only shape a Gemini Idea Expansion response may take: up to
    `MAX_IDEA_EXPANSION_ITEMS` typed, tiered items per category. There is deliberately no field
    here for venture_positioning, funding score, or any other Judge-owned value — Gemini can only
    ever add candidate ideas, never change a decision already made elsewhere (see
    app.agents.idea_expansion_reviewer for the additional safety checks applied before any of this
    is merged onto the deterministic baseline).
    """

    customer_segments: list[GeminiIdeaExpansionItem] = Field(default_factory=list)
    adjacent_industries: list[GeminiIdeaExpansionItem] = Field(default_factory=list)
    feature_ideas: list[GeminiIdeaExpansionItem] = Field(default_factory=list)
    pricing_models: list[GeminiIdeaExpansionItem] = Field(default_factory=list)
    pivot_opportunities: list[GeminiIdeaExpansionItem] = Field(default_factory=list)
    partnerships: list[GeminiIdeaExpansionItem] = Field(default_factory=list)
    go_to_market: list[GeminiIdeaExpansionItem] = Field(default_factory=list)

    @field_validator(
        "customer_segments", "adjacent_industries", "feature_ideas", "pricing_models",
        "pivot_opportunities", "partnerships", "go_to_market",
        mode="before",
    )
    @classmethod
    def _bound_items(cls, value: object) -> list:
        return _bounded_idea_items(value)


class GeminiCompetitorPossibilities(BaseModel):
    """The only shape a competitor-possibilities reviewer response may take: a bounded list of
    typed, category-level possibilities (see `GeminiCompetitorPossibility`). Each raw item is
    validated and safety-checked independently — an invalid item (wrong shape, a named company, a
    URL/email/corporate suffix) is silently discarded rather than causing the whole response to
    fail; a partial, safe list is more useful than discarding everything over one bad entry.
    """

    possibilities: list[GeminiCompetitorPossibility] = Field(default_factory=list)

    @field_validator("possibilities", mode="before")
    @classmethod
    def _sanitize_possibilities(cls, value: object) -> list[GeminiCompetitorPossibility]:
        if not isinstance(value, list):
            return []
        cleaned: list[GeminiCompetitorPossibility] = []
        for raw in value[:MAX_COMPETITOR_POSSIBILITIES]:
            item = _validate_one_possibility(raw)
            if item is not None:
                cleaned.append(item)
        return cleaned


MAX_STRATEGIC_ITEMS = 4
MAX_STRATEGIC_TEXT_LENGTH = 320


class GeminiStrategicConfidenceTier(str, Enum):
    """Gemini's Strategic Opportunity items may only ever claim one of these two tiers — same
    structural guarantee as GeminiIdeaConfidenceTier (Phase 2): "confirmed_from_evidence" is
    reserved for app.agents.strategic_opportunity's own deterministic reasoning, never for a
    Gemini-authored item."""

    REASONABLE_HYPOTHESIS = "reasonable_hypothesis"
    SPECULATIVE_FUTURE_OPPORTUNITY = "speculative_future_opportunity"


class StrategicOpportunityContext(BaseModel):
    """Read-only facts sent to the Gemini Strategic Opportunity reviewer (Phase 3). Every fact
    here was already computed deterministically — Gemini's job is to add additional reasoned
    adjacent markets, future-form possibilities, and strategic risks, never to alter venture
    positioning, funding readiness, mentor verdict, or any other Judge-owned field.
    """

    startup_name: str
    startup_description: str
    primary_domain: str | None = None
    secondary_domains: list[str] = Field(default_factory=list)
    deployment_sectors: list[str] = Field(default_factory=list)
    funding_level: str
    market_summary: str = ""
    business_model_summary: str = ""
    competitor_summary: str = ""
    present_capability_labels: list[str] = Field(default_factory=list)


class GeminiStrategicOpportunityItem(BaseModel):
    opportunity: str = Field(max_length=MAX_STRATEGIC_TEXT_LENGTH)
    reason: str = Field(max_length=MAX_STRATEGIC_TEXT_LENGTH)
    evidence: str = Field(max_length=MAX_STRATEGIC_TEXT_LENGTH)
    confidence_tier: GeminiStrategicConfidenceTier
    recommended_next_step: str = Field(max_length=MAX_STRATEGIC_TEXT_LENGTH)

    @field_validator("opportunity", "reason", "evidence", "recommended_next_step")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class GeminiRiskCategory(str, Enum):
    MARKET = "market"
    TIMING = "timing"
    REGULATORY = "regulatory"
    TECHNOLOGY = "technology"
    COMPETITION = "competition"
    ADOPTION = "adoption"


class GeminiRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GeminiStrategicRisk(BaseModel):
    risk: str = Field(max_length=MAX_STRATEGIC_TEXT_LENGTH)
    category: GeminiRiskCategory
    why: str = Field(max_length=MAX_STRATEGIC_TEXT_LENGTH)
    likelihood: GeminiRiskLevel
    impact: GeminiRiskLevel
    mitigation: str = Field(max_length=MAX_STRATEGIC_TEXT_LENGTH)
    confidence_tier: GeminiStrategicConfidenceTier

    @field_validator("risk", "why", "mitigation")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


def _bounded_strategic_items(value: object) -> list:
    if not isinstance(value, list):
        return []
    return value[:MAX_STRATEGIC_ITEMS]


class GeminiStrategicOpportunity(BaseModel):
    """The only shape a Gemini Strategic Opportunity response may take: up to
    `MAX_STRATEGIC_ITEMS` typed, tiered items for `adjacent_opportunities`/`future_expansion`, and
    up to `MAX_STRATEGIC_ITEMS` typed risks for `strategic_risks`. There is deliberately no field
    here for `primary_opportunity` (that stays fully deterministic — see
    app.agents.strategic_opportunity), venture_positioning, or any other Judge-owned value — Gemini
    can only ever add candidate reasoning, never change a decision already made elsewhere (see
    app.agents.strategic_opportunity_reviewer for the additional safety checks applied before any
    of this is merged onto the deterministic baseline).
    """

    adjacent_opportunities: list[GeminiStrategicOpportunityItem] = Field(default_factory=list)
    future_expansion: list[GeminiStrategicOpportunityItem] = Field(default_factory=list)
    strategic_risks: list[GeminiStrategicRisk] = Field(default_factory=list)

    @field_validator("adjacent_opportunities", "future_expansion", "strategic_risks", mode="before")
    @classmethod
    def _bound_items(cls, value: object) -> list:
        return _bounded_strategic_items(value)
