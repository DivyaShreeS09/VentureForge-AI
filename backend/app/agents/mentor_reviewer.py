"""Safe, never-raising Gemini mentor reviewer wrapper (Full Mentor Orchestration phase).

`review_mentor_safely` is the only entry point the orchestrator calls. It always returns a
complete, schema-valid MentorInterpretation dict: the deterministic baseline
(app.agents.mentor_synthesis.build_deterministic_mentor) unchanged whenever Gemini is
unconfigured, unavailable, times out, returns malformed/invalid JSON, or its response fails any of
the safety checks below — and the baseline with a narrow, validated subset of narrative fields
replaced by Gemini's rephrasing otherwise.

Safety contract (see `merge_gemini_narrative_into_baseline`):
  - Every Judge-owned or structural field (venture_positioning, feature_gap_analysis,
    validation_plan, roadmap_30_60_90, top_next_actions, evidence_and_uncertainty,
    mvp_recommendation's target_user/included_capabilities/excluded_for_now, mentor_verdict's
    readiness_level) is ALWAYS taken from the deterministic baseline — Gemini's schema
    (GeminiMentorInterpretation) has no field for any of these, so there is nothing to merge even
    if a raw response tried to include one (extra keys are silently ignored by Pydantic).
  - Gemini may only replace: idea_understanding's text fields, customer_and_market,
    business_model, competitor_landscape, revenue_scenarios, mentor_verdict's
    concise_verdict/strongest_signal/biggest_risk/immediate_priority, and mvp_recommendation's
    single_core_problem/minimum_workflow/success_metric/pilot_environment/reasons.
  - Even within that allowed subset, the whole Gemini contribution is rejected (falling back to
    100% deterministic) if: it introduces any number not already present in the startup
    description or the deterministic baseline (a cheap, effective invented-traction/invented-
    numeric-claim guard), or it contains an unattested two-or-more-word Title-Case sequence not
    already present in the startup name, venture positioning domains/sectors, or founder-supplied
    competitor names (a cheap, effective invented-competitor/invented-company guard).
"""

from __future__ import annotations

import json
import logging
import re

from app.ai.base import LLMUnavailable
from app.ai.factory import get_llm_provider
from app.ai.schemas import GeminiMentorInterpretation, MentorContext

logger = logging.getLogger(__name__)

_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
_TITLE_CASE_SEQUENCE = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)+\b")

_NARRATIVE_TEXT_FIELDS = (
    "idea_summary", "idea_target_user", "idea_problem", "idea_proposed_solution",
    "idea_business_context", "customer_and_market", "business_model", "competitor_landscape",
    "revenue_scenarios", "concise_verdict", "strongest_signal", "biggest_risk",
    "immediate_priority", "mvp_single_core_problem", "mvp_minimum_workflow",
    "mvp_success_metric", "mvp_pilot_environment",
)


def _numbers_in(text: str) -> set[str]:
    return set(_NUMBER_PATTERN.findall(text or ""))


def _title_case_sequences_in(text: str) -> set[str]:
    return set(_TITLE_CASE_SEQUENCE.findall(text or ""))


def _all_gemini_text(gemini: GeminiMentorInterpretation) -> str:
    parts = [getattr(gemini, field) for field in _NARRATIVE_TEXT_FIELDS]
    parts.extend(gemini.mvp_reasons)
    return " ".join(parts)


def _known_names_from_baseline(baseline: dict, startup_name: str) -> set[str]:
    """Every legitimate multi-word Title-Case sequence this response is allowed to contain: the
    startup's own name, plus anything already present anywhere in the deterministic baseline
    (rubric dimension labels like "Problem Clarity", capability labels, the venture positioning
    domain, any founder-submitted competitor name already recorded in competitor_landscape, etc.)
    — since none of that was invented by Gemini, it's definitionally safe. Anything else that
    looks like a two-or-more-word proper noun is treated as a possible invented company/claim."""
    known: set[str] = set()
    known |= _title_case_sequences_in(startup_name)
    known |= _title_case_sequences_in(json.dumps(baseline))
    return known


def merge_gemini_narrative_into_baseline(
    gemini: GeminiMentorInterpretation, baseline: dict, startup_name: str, startup_description: str
) -> dict | None:
    """Returns the merged mentor dict, or None if the response fails any safety check (callers
    must fall back to the untouched `baseline` in that case)."""
    allowed_numbers = _numbers_in(startup_description) | _numbers_in(json.dumps(baseline))
    gemini_text = _all_gemini_text(gemini)
    if _numbers_in(gemini_text) - allowed_numbers:
        logger.info("Gemini mentor response rejected: introduced an unsupported numeric claim")
        return None

    known_names = _known_names_from_baseline(baseline, startup_name)
    for sequence in _title_case_sequences_in(gemini_text):
        if sequence not in known_names:
            logger.info("Gemini mentor response rejected: unattested proper-noun sequence %r", sequence)
            return None

    merged = dict(baseline)
    merged["idea_understanding"] = {
        "summary": gemini.idea_summary,
        "target_user": gemini.idea_target_user,
        "problem": gemini.idea_problem,
        "proposed_solution": gemini.idea_proposed_solution,
        "business_context": gemini.idea_business_context,
    }
    merged["customer_and_market"] = gemini.customer_and_market
    merged["business_model"] = gemini.business_model
    merged["competitor_landscape"] = gemini.competitor_landscape
    merged["revenue_scenarios"] = gemini.revenue_scenarios
    merged["mentor_verdict"] = {
        **baseline["mentor_verdict"],
        "concise_verdict": gemini.concise_verdict,
        "strongest_signal": gemini.strongest_signal,
        "biggest_risk": gemini.biggest_risk,
        "immediate_priority": gemini.immediate_priority,
    }
    merged["mvp_recommendation"] = {
        **baseline["mvp_recommendation"],
        "single_core_problem": gemini.mvp_single_core_problem,
        "minimum_workflow": gemini.mvp_minimum_workflow,
        "success_metric": gemini.mvp_success_metric,
        "pilot_environment": gemini.mvp_pilot_environment,
        "reasons": gemini.mvp_reasons or baseline["mvp_recommendation"]["reasons"],
    }
    merged["source"] = "gemini"
    merged["source_attribution"] = {
        **baseline["source_attribution"],
        "idea_understanding": "Gemini rephrasing of deterministic facts (schema/safety-validated)",
        "customer_and_market": "Gemini rephrasing of deterministic facts (schema/safety-validated)",
        "business_model": "Gemini rephrasing of deterministic facts (schema/safety-validated)",
        "competitor_landscape": "Gemini rephrasing of deterministic facts (schema/safety-validated)",
        "revenue_scenarios": "Gemini rephrasing of deterministic facts (schema/safety-validated)",
        "mentor_verdict": "Gemini rephrasing of deterministic facts (schema/safety-validated); readiness_level unchanged",
        "mvp_recommendation": "Gemini rephrasing of deterministic facts (schema/safety-validated); scope/capabilities unchanged",
    }
    return merged


def build_mentor_context(startup_name: str, startup_description: str, baseline: dict) -> MentorContext:
    """Build the `MentorContext` sent to the optional Gemini mentor reviewer from an already-built
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
    """Never raises. Returns `baseline` unchanged unless Gemini is configured, responds, passes
    schema validation, and passes every safety check above."""
    provider = get_llm_provider()
    if provider is None:
        return baseline

    try:
        gemini_response = provider.generate_mentor_interpretation(context)
    except LLMUnavailable as exc:
        logger.info("Gemini mentor reviewer unavailable, falling back to deterministic mentor: %s", exc)
        return baseline
    except Exception:
        logger.exception("Unexpected error calling the Gemini mentor reviewer; falling back to deterministic mentor")
        return baseline

    merged = merge_gemini_narrative_into_baseline(gemini_response, baseline, startup_name, startup_description)
    return merged if merged is not None else baseline
