"""Provider-neutral interface for the optional LLM narrative layer.

Any provider (Gemini today; other hosted or local models later, if ever added) implements this Protocol.
Nothing outside `backend/app/ai/` imports a specific provider — callers only ever see
`LLMProvider` and go through `backend/app/ai/factory.py` to get one (or None).
"""

from __future__ import annotations

from typing import Protocol

from app.ai.schemas import (
    CompetitorPossibilitiesContext,
    GeminiCompetitorPossibilities,
    GeminiIdeaExpansion,
    GeminiMentorAdvice,
    GeminiPositioningRecommendation,
    GeminiStrategicOpportunity,
    IdeaExpansionContext,
    MentorContext,
    NarrativeContext,
    NarrativeEnhancement,
    PositioningReviewContext,
    StrategicOpportunityContext,
)


class LLMUnavailable(RuntimeError):
    """Raised by any provider for every failure mode: missing/invalid key, timeout, rate limit,
    network error, malformed JSON, or a response that fails schema validation. Callers only ever
    need to catch this one exception type to fall back to the deterministic path."""


class LLMProvider(Protocol):
    def generate_narrative(self, context: NarrativeContext) -> NarrativeEnhancement:
        """Return a validated narrative enhancement, or raise LLMUnavailable."""
        ...

    def review_positioning(self, context: PositioningReviewContext) -> GeminiPositioningRecommendation:
        """Return a validated, schema-constrained positioning recommendation, or raise
        LLMUnavailable. Purely advisory — see app.agents.venture_positioning for how the Judge
        Agent (the sole final authority) weighs this."""
        ...

    def suggest_competitor_possibilities(
        self, context: CompetitorPossibilitiesContext
    ) -> GeminiCompetitorPossibilities:
        """Return a validated, sanitized list of category-level competitor possibilities, or raise
        LLMUnavailable. Never a named company — see app.agents.competitor_agent."""
        ...

    def generate_mentor_advice(self, context: MentorContext) -> GeminiMentorAdvice:
        """Return a validated, schema-bounded list of tagged mentor advice (Product Intelligence
        Sprint: enrichment, not rephrasing), or raise LLMUnavailable. Purely additive and advisory
        — see app.agents.mentor_reviewer.enrich_mentor_safely, which appends only safety-checked
        items onto the deterministic mentor baseline; every existing baseline field (positioning,
        verdict, roadmap, idea understanding, etc.) is always the deterministic value regardless of
        this response."""
        ...

    def generate_idea_expansion(self, context: IdeaExpansionContext) -> GeminiIdeaExpansion:
        """Return a validated, schema-bounded set of additional Idea Expansion possibilities, or
        raise LLMUnavailable. Purely additive and advisory — see app.agents.idea_expansion_reviewer,
        which appends only safety-checked items onto the deterministic Idea Expansion baseline;
        nothing here can replace or alter venture positioning, funding readiness, or any other
        Judge-owned field."""
        ...

    def generate_strategic_opportunity(self, context: StrategicOpportunityContext) -> GeminiStrategicOpportunity:
        """Return a validated, schema-bounded set of additional adjacent-market/future-expansion
        reasoning and strategic risks, or raise LLMUnavailable. Purely additive and advisory — see
        app.agents.strategic_opportunity_reviewer, which appends only safety-checked items onto the
        deterministic Strategic Opportunity baseline; `primary_opportunity` and every Judge-owned
        field remain entirely deterministic regardless of this response."""
        ...
