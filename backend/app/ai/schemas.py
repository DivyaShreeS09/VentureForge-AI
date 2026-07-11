"""Pydantic contracts for the optional LLM narrative layer.

`NarrativeContext` is what the deterministic pipeline sends to a provider — it contains only
already-computed facts (predictions, scores, user-provided answers), never raw instructions.
`NarrativeEnhancement` is what a provider must return; every field is length- and count-bounded so
a malformed or oversized response is rejected by validation rather than rendered as-is, and so the
narrative can never smuggle in something the size of a second industry classification or score.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

MAX_SUMMARY_LENGTH = 600
MAX_LIST_ITEMS = 6
MAX_ITEM_LENGTH = 220


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
