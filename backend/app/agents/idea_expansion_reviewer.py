"""Safe, never-raising Gemini Idea Expansion reviewer wrapper (Phase 2).

`generate_idea_expansion_safely` is the only entry point callers use. It always returns a complete
Idea Expansion dict: the deterministic baseline
(app.agents.idea_expansion.build_deterministic_idea_expansion) unchanged whenever Gemini is
unconfigured, unavailable, times out, or returns malformed/invalid JSON — plus, when a valid
response passes every safety check below, one or more additional items APPENDED (never replacing)
to each category.

Safety contract:
  - Gemini's schema (GeminiIdeaExpansionItem.confidence_tier) only allows "reasonable_hypothesis"
    or "speculative_future_opportunity" — it structurally cannot claim "confirmed_from_evidence"
    (see app.ai.schemas.GeminiIdeaConfidenceTier), so a Gemini-authored item can never be presented
    with the same certainty as a deterministic one.
  - Every item is rejected if it contains a URL, email address, or corporate legal suffix (Inc,
    LLC, Ltd, Corp, GmbH, etc — see app.ai.schemas's patterns, reused here).
  - Every category except `partnerships` additionally rejects any multi-word Title-Case sequence
    (a likely proper-noun brand/company name, e.g. "Toast POS Systems") that isn't already known —
    "known" means already present in this venture's own context (its domain names, deployment
    sectors, capability labels, or startup name). Idea Expansion titles are natural sentences (e.g.
    "Offline mode"), unlike the enforced-lowercase category phrases used elsewhere in this system,
    so a single capitalized word is never itself treated as suspicious — only an unattested
    multi-word sequence is (the same shape of guard app.agents.mentor_reviewer uses).
  - `partnerships` is exempt from the proper-noun guard because naming a realistic potential
    partner organization (a university, a payments provider, a cloud vendor) is the intended output
    for that one category, not an invented-competitor claim — it is still checked for
    URLs/emails/corporate suffixes.
  - A single item failing its check only drops that one item, never the whole response.
"""

from __future__ import annotations

import logging
import re

from app.ai.base import LLMUnavailable
from app.ai.factory import get_llm_provider
from app.ai.schemas import _CORPORATE_SUFFIX_PATTERN, _EMAIL_PATTERN, _URL_OR_DOMAIN_PATTERN, GeminiIdeaExpansion, IdeaExpansionContext

logger = logging.getLogger(__name__)

_CATEGORIES = (
    "customer_segments",
    "adjacent_industries",
    "feature_ideas",
    "pricing_models",
    "pivot_opportunities",
    "partnerships",
    "go_to_market",
)

# Only `partnerships` is allowed to name a real organization — every other category is checked
# against the stricter proper-noun guard too.
_ALLOW_NAMED_ENTITIES = {"partnerships"}

_TITLE_CASE_SEQUENCE = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)+\b")


def _known_names(context: IdeaExpansionContext) -> set[str]:
    """Every legitimate multi-word Title-Case sequence a response is allowed to contain: this
    venture's own domain names, deployment sectors, capability labels, and its own startup name —
    since none of that was invented by Gemini, it's definitionally safe."""
    known: set[str] = set()
    texts = [
        context.startup_name,
        context.primary_domain or "",
        *context.secondary_domains,
        *context.deployment_sectors,
        *context.present_capability_labels,
        *context.recommended_capability_labels,
    ]
    for text in texts:
        known |= set(_TITLE_CASE_SEQUENCE.findall(text))
    return known


def build_idea_expansion_context(
    startup_name: str,
    startup_description: str,
    venture_positioning: dict,
    feature_gap: dict,
    mvp_recommendation: dict,
    funding_level: str,
) -> IdeaExpansionContext:
    return IdeaExpansionContext(
        startup_name=startup_name,
        startup_description=startup_description,
        primary_domain=venture_positioning.get("primary_domain"),
        secondary_domains=venture_positioning.get("secondary_domains") or [],
        deployment_sectors=venture_positioning.get("deployment_sectors") or [],
        funding_level=funding_level,
        present_capability_labels=[c["label"] for c in feature_gap.get("present_capabilities", [])],
        recommended_capability_labels=[c["label"] for c in feature_gap.get("recommended_capabilities", [])],
        mvp_single_core_problem=mvp_recommendation.get("single_core_problem", ""),
    )


def _passes_safety_check(title: str, reason: str, allow_named_entities: bool, known_names: set[str]) -> bool:
    """Checks `title` and `reason` independently rather than concatenating them — concatenating
    could accidentally form a spurious multi-word Title-Case sequence across the field boundary
    (e.g. a title ending in "Airports" immediately followed by a reason starting with "Airports")
    that neither field contains on its own."""
    for text in (title, reason):
        if _URL_OR_DOMAIN_PATTERN.search(text) or _EMAIL_PATTERN.search(text):
            return False
        if allow_named_entities:
            continue
        if _CORPORATE_SUFFIX_PATTERN.search(text):
            return False
        if any(seq not in known_names for seq in _TITLE_CASE_SEQUENCE.findall(text)):
            return False
    return True


def merge_gemini_idea_expansion_into_baseline(
    gemini: GeminiIdeaExpansion, baseline: dict, context: IdeaExpansionContext | None = None
) -> dict:
    """Returns a new dict — `baseline` plus any safety-checked Gemini items appended per category.
    Never mutates `baseline` in place. `context` supplies the "known names" an item is allowed to
    mention (see `_known_names`) — omit only when no venture context is available (every item is
    then held to the stricter "no multi-word Title-Case sequence at all" standard)."""
    known_names = _known_names(context) if context is not None else set()
    merged = dict(baseline)
    any_added = False

    for category in _CATEGORIES:
        allow_named = category in _ALLOW_NAMED_ENTITIES
        accepted = [
            {
                "title": item.title,
                "reason": item.reason,
                "confidence_tier": item.confidence_tier.value,
                "source": "gemini",
            }
            for item in getattr(gemini, category)
            if _passes_safety_check(item.title, item.reason, allow_named, known_names)
        ]
        if accepted:
            any_added = True
        merged[category] = [*merged.get(category, []), *accepted]

    merged["source"] = "gemini_enhanced" if any_added else merged.get("source", "deterministic")
    return merged


def generate_idea_expansion_safely(context: IdeaExpansionContext, baseline: dict) -> dict:
    """Never raises. Returns `baseline` unchanged unless Gemini is configured, responds, and
    passes schema validation — a response that fails validation entirely (not just one bad item)
    still falls back to the untouched baseline, exactly like every other Gemini reviewer in this
    codebase (see app.agents.mentor_reviewer, app.agents.competitor_reviewer)."""
    provider = get_llm_provider()
    if provider is None:
        return baseline

    try:
        gemini_response = provider.generate_idea_expansion(context)
    except LLMUnavailable as exc:
        logger.info("Gemini idea expansion reviewer unavailable, falling back to deterministic baseline: %s", exc)
        return baseline
    except Exception:
        logger.exception("Unexpected error calling the Gemini idea expansion reviewer; falling back to deterministic baseline")
        return baseline

    return merge_gemini_idea_expansion_into_baseline(gemini_response, baseline, context)
