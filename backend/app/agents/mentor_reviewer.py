"""Safe, never-raising Gemini mentor advisor wrapper (Full Mentor Orchestration phase).

Product Intelligence Sprint redesign: Gemini used to be restricted to rephrasing a narrow subset
of the deterministic mentor baseline's narrative fields (replacing them in place — see git history
for the prior `merge_gemini_narrative_into_baseline`). That made Gemini a paraphrasing engine, not
a mentor. This module now does the opposite: the deterministic baseline is NEVER touched, rephrased,
or replaced — Gemini instead contributes a bounded list of new, explicitly-tagged advice items
(`GeminiMentorAdvice`) appended under `mentor_advice_items`, covering domains (feature ideas,
differentiation, GTM, pricing rationale, pilot strategy, marketing, customer acquisition,
fundraising guidance, roadmap, execution advice, risk mitigation, alternative business models,
growth experiments) the deterministic system does not itself reason about.

`review_mentor_safely` is the only entry point the orchestrator/analysis_service call. It always
returns a complete mentor dict: the deterministic baseline with `mentor_advice_items: []` whenever
Gemini is unconfigured, unavailable, times out, returns malformed/invalid JSON, or every one of its
items fails safety checks — and the baseline with `mentor_advice_items` populated by whichever items
pass every check below otherwise. `source`/every existing baseline field is untouched either way.

Safety contract (see `_safe_advice_items`):
  - Structural (schema-level, see app.ai.schemas.GeminiMentorAdviceItem): `category` can never be
    "evidence" — that value is rejected at validation time, before this module ever sees it.
  - Per item, independently (one bad item drops only that item, never the whole list — same
    pattern as app.agents.idea_expansion_reviewer/strategic_opportunity_reviewer/
    competitor_reviewer): reject any item introducing a number (a count, dollar figure, percentage)
    not already present in the startup description or the deterministic baseline (blocks invented
    market sizes, customer counts, factual prices, accuracy numbers, statistics); reject any item
    containing an unattested two-or-more-word Title-Case sequence not already known from this
    venture's own context (blocks invented competitors/companies/regulation names presented as
    fact); reject any item matching a citation-style claim pattern ("according to", "studies show",
    "source:", ...) since Gemini cannot have performed real external research (blocks invented
    citations/research results).
"""

from __future__ import annotations

import json
import logging
import re

from app.ai.base import LLMUnavailable
from app.ai.factory import get_llm_provider
from app.ai.schemas import _CITATION_CLAIM_PATTERN, GeminiMentorAdvice, GeminiMentorAdviceItem, MentorContext

logger = logging.getLogger(__name__)

_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
_TITLE_CASE_SEQUENCE = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)+\b")


def _numbers_in(text: str) -> set[str]:
    return set(_NUMBER_PATTERN.findall(text or ""))


def _title_case_sequences_in(text: str) -> set[str]:
    return set(_TITLE_CASE_SEQUENCE.findall(text or ""))


def _known_names_from_baseline(baseline: dict, startup_name: str) -> set[str]:
    """Every legitimate multi-word Title-Case sequence an advice item is allowed to contain: the
    startup's own name, plus anything already present anywhere in the deterministic baseline
    (rubric dimension labels, capability labels, the venture positioning domain, any
    founder-submitted competitor name already recorded, etc.) — since none of that was invented by
    Gemini, it's definitionally safe. Anything else that looks like a two-or-more-word proper noun
    is treated as a possible invented company/claim."""
    known: set[str] = set()
    known |= _title_case_sequences_in(startup_name)
    known |= _title_case_sequences_in(json.dumps(baseline))
    return known


def _safe_advice_items(
    advice: GeminiMentorAdvice, baseline: dict, startup_name: str, startup_description: str
) -> list[dict]:
    """Filter Gemini's proposed advice items down to only those that pass every safety check,
    independently per item. Returns plain dicts ready to attach to the mentor result."""
    allowed_numbers = _numbers_in(startup_description) | _numbers_in(json.dumps(baseline))
    known_names = _known_names_from_baseline(baseline, startup_name)

    safe_items: list[dict] = []
    for item in advice.advice:
        if _numbers_in(item.text) - allowed_numbers:
            logger.info("Gemini mentor advice item rejected: introduced an unsupported numeric claim")
            continue
        unattested = [seq for seq in _title_case_sequences_in(item.text) if seq not in known_names]
        if unattested:
            logger.info("Gemini mentor advice item rejected: unattested proper-noun sequence %r", unattested)
            continue
        if _CITATION_CLAIM_PATTERN.search(item.text):
            logger.info("Gemini mentor advice item rejected: citation/research-claim pattern")
            continue
        safe_items.append(item.model_dump())
    return safe_items


def build_mentor_context(startup_name: str, startup_description: str, baseline: dict) -> MentorContext:
    """Build the `MentorContext` sent to the optional Gemini mentor advisor from an already-built
    deterministic baseline (see app.agents.mentor_synthesis.build_deterministic_mentor). Shared by
    both the orchestrator's `mentor_synthesis_node` (a fresh analysis run) and
    app.services.analysis_service's regeneration helpers (a founder-triggered positioning/revenue
    correction) — kept in exactly one place so the two call sites can never drift apart.
    """
    return MentorContext(
        startup_name=startup_name,
        startup_description=startup_description,
        venture_positioning_text=baseline["venture_positioning"],
        strengths=baseline["strengths"],
        real_weaknesses=baseline["real_weaknesses"],
        funding_level=baseline["mentor_verdict"]["readiness_level"],
        customer_and_market_facts=baseline["customer_and_market"],
        business_model_facts=baseline["business_model"],
        competitor_landscape_facts=baseline["competitor_landscape"],
        revenue_scenarios_facts=baseline["revenue_scenarios"],
        mvp_single_core_problem_facts=baseline["mvp_recommendation"]["single_core_problem"],
        mvp_minimum_workflow_facts=baseline["mvp_recommendation"]["minimum_workflow"],
        mvp_success_metric_facts=baseline["mvp_recommendation"]["success_metric"],
        mvp_pilot_environment_facts=baseline["mvp_recommendation"]["pilot_environment"],
        idea_understanding_facts=baseline["idea_understanding"],
    )


def review_mentor_safely(context: MentorContext, baseline: dict, startup_name: str, startup_description: str) -> dict:
    """Never raises. Always returns the deterministic `baseline` with `mentor_advice_items` set —
    empty unless Gemini is configured, responds, passes schema validation, and at least one item
    passes every safety check above. `source` and every other baseline field are never altered."""
    result = dict(baseline)
    result.setdefault("mentor_advice_items", [])

    provider = get_llm_provider()
    if provider is None:
        return result

    try:
        gemini_response = provider.generate_mentor_advice(context)
    except LLMUnavailable as exc:
        logger.info("Gemini mentor advisor unavailable, proceeding with no advice items: %s", exc)
        return result
    except Exception:
        logger.exception("Unexpected error calling the Gemini mentor advisor; proceeding with no advice items")
        return result

    result["mentor_advice_items"] = _safe_advice_items(gemini_response, baseline, startup_name, startup_description)
    return result
