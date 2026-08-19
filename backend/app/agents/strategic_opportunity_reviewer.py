"""Safe, never-raising Gemini Strategic Opportunity reviewer wrapper (Phase 3).

`generate_strategic_opportunity_safely` is the only entry point callers use. It always returns a
complete Strategic Opportunity dict: the deterministic baseline
(app.agents.strategic_opportunity.build_deterministic_strategic_opportunity) unchanged whenever
Gemini is unconfigured, unavailable, times out, or returns malformed/invalid JSON — plus, when a
valid response passes every safety check below, additional items APPENDED (never replacing) to
`adjacent_opportunities`/`future_expansion`/`strategic_risks`. `primary_opportunity` is never
touched by Gemini at all — it is not part of the Gemini schema (see app.ai.schemas.
GeminiStrategicOpportunity), so there is nothing for Gemini to merge into it even if it tried.

Safety contract — identical shape to app.agents.idea_expansion_reviewer (Phase 2):
  - Gemini's schema (confidence_tier) only allows "reasonable_hypothesis" or
    "speculative_future_opportunity" — it structurally cannot claim "confirmed_from_evidence".
  - Every item is rejected if it contains a URL, email address, corporate legal suffix, or an
    unattested multi-word Title-Case sequence (a likely proper-noun brand/company name) not
    already known from this venture's own context.
  - A single item failing its check only drops that one item, never the whole response.
"""

from __future__ import annotations

import logging
import re

from app.ai.base import LLMUnavailable
from app.ai.factory import get_llm_provider
from app.ai.schemas import _CORPORATE_SUFFIX_PATTERN, _EMAIL_PATTERN, _URL_OR_DOMAIN_PATTERN, GeminiStrategicOpportunity, StrategicOpportunityContext

logger = logging.getLogger(__name__)

_ITEM_CATEGORIES = ("adjacent_opportunities", "future_expansion")

_TITLE_CASE_SEQUENCE = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)+\b")


def _known_names(context: StrategicOpportunityContext) -> set[str]:
    """Every legitimate multi-word Title-Case sequence a response is allowed to contain: this
    venture's own domain names, deployment sectors, capability labels, and its own startup name."""
    known: set[str] = set()
    texts = [
        context.startup_name,
        context.primary_domain or "",
        *context.secondary_domains,
        *context.deployment_sectors,
        *context.present_capability_labels,
    ]
    for text in texts:
        known |= set(_TITLE_CASE_SEQUENCE.findall(text))
    return known


def build_strategic_opportunity_context(
    startup_name: str,
    startup_description: str,
    venture_positioning: dict,
    market_intelligence: dict | None,
    business_model: dict | None,
    competitor_analysis: dict | None,
    feature_gap: dict,
    funding_level: str,
) -> StrategicOpportunityContext:
    verified = (competitor_analysis or {}).get("verified_competitors") or []
    return StrategicOpportunityContext(
        startup_name=startup_name,
        startup_description=startup_description,
        primary_domain=venture_positioning.get("primary_domain"),
        secondary_domains=venture_positioning.get("secondary_domains") or [],
        deployment_sectors=venture_positioning.get("deployment_sectors") or [],
        funding_level=funding_level,
        market_summary=(market_intelligence or {}).get("market_summary", ""),
        business_model_summary=(business_model or {}).get("value_proposition", ""),
        competitor_summary=", ".join(c["name"] for c in verified) if verified else "No verified competitors named.",
        present_capability_labels=[c["label"] for c in feature_gap.get("present_capabilities", [])],
    )


def _passes_safety_check(*fields: str, known_names: set[str]) -> bool:
    """Checks each field independently rather than concatenating them — concatenating adjacent
    fields (e.g. a title ending in a capitalized word immediately followed by a reason starting
    with one) can accidentally form a spurious multi-word Title-Case sequence across the field
    boundary that neither field contains on its own."""
    for text in fields:
        if _URL_OR_DOMAIN_PATTERN.search(text) or _EMAIL_PATTERN.search(text) or _CORPORATE_SUFFIX_PATTERN.search(text):
            return False
        if any(seq not in known_names for seq in _TITLE_CASE_SEQUENCE.findall(text)):
            return False
    return True


def merge_gemini_strategic_opportunity_into_baseline(
    gemini: GeminiStrategicOpportunity, baseline: dict, context: StrategicOpportunityContext | None = None
) -> dict:
    """Returns a new dict — `baseline` plus any safety-checked Gemini items appended to
    `adjacent_opportunities`/`future_expansion`/`strategic_risks`. `primary_opportunity` is always
    copied through unchanged. Never mutates `baseline` in place."""
    known_names = _known_names(context) if context is not None else set()
    merged = dict(baseline)
    any_added = False

    for category in _ITEM_CATEGORIES:
        accepted = [
            {
                "opportunity": item.opportunity,
                "reason": item.reason,
                "evidence": item.evidence,
                "confidence_tier": item.confidence_tier.value,
                "recommended_next_step": item.recommended_next_step,
                "potential_revenue": "Not yet quantified — a new opportunity requires its own validation.",
                "difficulty": "medium",
                "time_to_market": "3-6 months",
                "validation_effort": "1-2 discovery interviews",
                "suitable_stage": "pilot",
                "source": "gemini",
            }
            for item in getattr(gemini, category)
            if _passes_safety_check(item.opportunity, item.reason, item.evidence, known_names=known_names)
        ]
        if accepted:
            any_added = True
        merged[category] = [*merged.get(category, []), *accepted]

    accepted_risks = [
        {
            "risk": risk.risk,
            "category": risk.category.value,
            "why": risk.why,
            "likelihood": risk.likelihood.value,
            "impact": risk.impact.value,
            "mitigation": risk.mitigation,
            "confidence_tier": risk.confidence_tier.value,
            "source": "gemini",
        }
        for risk in gemini.strategic_risks
        if _passes_safety_check(risk.risk, risk.why, risk.mitigation, known_names=known_names)
    ]
    if accepted_risks:
        any_added = True
    merged["strategic_risks"] = [*merged.get("strategic_risks", []), *accepted_risks]

    merged["source"] = "gemini_enhanced" if any_added else merged.get("source", "deterministic")
    return merged


def generate_strategic_opportunity_safely(context: StrategicOpportunityContext, baseline: dict) -> dict:
    """Never raises. Returns `baseline` unchanged unless Gemini is configured, responds, and
    passes schema validation — exactly like app.agents.idea_expansion_reviewer.
    generate_idea_expansion_safely."""
    provider = get_llm_provider()
    if provider is None:
        return baseline

    try:
        gemini_response = provider.generate_strategic_opportunity(context)
    except LLMUnavailable as exc:
        logger.info("Gemini strategic opportunity reviewer unavailable, falling back to deterministic baseline: %s", exc)
        return baseline
    except Exception:
        logger.exception("Unexpected error calling the Gemini strategic opportunity reviewer; falling back to deterministic baseline")
        return baseline

    return merge_gemini_strategic_opportunity_into_baseline(gemini_response, baseline, context)
