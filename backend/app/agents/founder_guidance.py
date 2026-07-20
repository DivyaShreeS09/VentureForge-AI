"""Structured founder-facing guidance items (Phase 1 mentor-language correction).

Replaces raw "weakness" strings (`f"{label}: {scale_description}"`) with one richly-typed item per
funding-readiness dimension: `dimension, category, status, title, observation, why_it_matters,
next_step, example, priority, evidence_state, source`. `strengths`/`weaknesses`/`real_weaknesses` in
`judge_summary` remain for backward compatibility only (see app.agents.judge.synthesize) — no new
code (app.agents.mentor_synthesis, the frontend) reads or parses those string fields; everything new
reads `founder_guidance_items`.

Category assignment for `confirmed_negative` is **not** automatically "confirmed_risk" — missing
answers, "not sure yet," lack of documentation, and early-stage status must never be treated as
flaws in the idea. `confirmed_risk` is reserved for genuinely adverse *confirmed* evidence (e.g.
documented customer rejection) that the current 8-dimension rubric does not collect, so none of
today's dimensions ever map `confirmed_negative` to `confirmed_risk` — see `_NEGATIVE_CATEGORY`.

Priority is a single deterministic ranking (category urgency, then the dimension's renormalized
rubric weight) shared by every consumer (validation plan, top actions, mentor verdict) so there is
exactly one prioritized ordering in the product, not several independently-computed ones.
"""

from __future__ import annotations

from app.agents.hypothesis_engine import build_hypothesis

FOUNDER_GUIDANCE_VERSION = "v1"

# Category assigned to a dimension's `confirmed_negative` state. Deliberately never
# "confirmed_risk" for any of today's 8 rubric dimensions — see module docstring.
_NEGATIVE_CATEGORY: dict[str, str] = {
    "problem_clarity": "improvement_opportunity",
    "customer_pain_evidence": "validation_opportunity",
    "market_size_evidence": "discovery_question",
    "product_maturity": "improvement_opportunity",
    "traction": "validation_opportunity",
    "revenue_model_clarity": "discovery_question",
    "team_completeness": "improvement_opportunity",
    "competitive_differentiation": "improvement_opportunity",
}

_STATUS_BY_CATEGORY: dict[str, str] = {
    "strength": "Confirmed strength",
    "improvement_opportunity": "Good start — can be strengthened",
    "discovery_question": "Discovery question",
    "validation_opportunity": "Validation opportunity",
    "confirmed_risk": "Confirmed risk",
    "future_enhancement": "Future enhancement",
}

# Coaching content for the two states the Hypothesis Engine doesn't already cover: a confirmed
# strength (severity 2) and a partial/improvable answer (severity 1). Every other non-strength
# category reuses `build_hypothesis(dimension)` (starting_hypothesis/validation_task) as its
# underlying coaching content — the advice "you don't know this yet, here's how to find out" is the
# same whether the founder said "not sure" or "no, not yet."
_POSITIVE_CONTENT: dict[str, dict[int, dict[str, str]]] = {
    "problem_clarity": {
        2: {"title": "Your problem statement is sharp.", "why_it_matters": "A specific, well-defined problem is one of the strongest early signals investors and customers look for.", "next_step": "Keep validating that the people you describe actually feel this problem as urgently as stated."},
        1: {"title": "You've named the problem, but broadly.", "why_it_matters": "Naming exactly who has the problem and what it costs them makes every later decision (pricing, MVP scope, marketing) easier.", "next_step": "Rewrite it as one sentence: who has this problem, and what does it cost them today?"},
    },
    "customer_pain_evidence": {
        2: {"title": "You have documented evidence customers feel this pain.", "why_it_matters": "Documented pain, not a hunch, is the foundation every other assumption builds on.", "next_step": "Keep expanding this evidence as you reach new customer segments."},
        1: {"title": "You have anecdotal evidence of customer pain.", "why_it_matters": "Anecdotes are a fine starting point; documented evidence makes the case far more convincing to investors and to yourself.", "next_step": "Turn a few of those anecdotes into structured interview notes or a short survey."},
    },
    "market_size_evidence": {
        2: {"title": "You have a sourced market-size estimate.", "why_it_matters": "A sourced TAM/SAM/SOM shows you understand the real opportunity, not just a hopeful guess.", "next_step": "Keep it current as your target segment narrows or expands."},
        1: {"title": "You have a rough market-size estimate.", "why_it_matters": "A rough estimate is a reasonable start; a sourced one is far more convincing to investors.", "next_step": "Find one or two public sources to back up your estimate."},
    },
    "product_maturity": {
        2: {"title": "You have a live product with real users.", "why_it_matters": "Real usage is the strongest possible signal — it beats any amount of planning.", "next_step": "Keep listening closely to how those users actually use it."},
        1: {"title": "You have a prototype or MVP.", "why_it_matters": "A working prototype de-risks the idea far more than a plan on paper.", "next_step": "Get it in front of one more real user this week and watch what happens."},
    },
    "traction": {
        2: {"title": "You have paying customers or recurring usage.", "why_it_matters": "Real traction is the single most convincing signal to investors and to yourself.", "next_step": "Keep tracking retention as closely as acquisition."},
        1: {"title": "You have early pilot users.", "why_it_matters": "Pilot users are exactly how traction starts — the next step is turning interest into a repeatable pattern.", "next_step": "Ask your pilot users directly what would make this worth paying for."},
    },
    "revenue_model_clarity": {
        2: {"title": "Your pricing and unit economics are clear.", "why_it_matters": "Clear unit economics let you make confident decisions about growth and spend.", "next_step": "Re-test your pricing as you learn more about willingness to pay."},
        1: {"title": "You have a rough pricing model.", "why_it_matters": "A rough model is a fine starting point; testing it with real prospects will sharpen it fast.", "next_step": "Price the offering to 3 prospective customers and compare reactions."},
    },
    "team_completeness": {
        2: {"title": "Your founding team covers the core skills this venture needs.", "why_it_matters": "A team that covers its own gaps moves faster and needs less outside help early on.", "next_step": "Keep an eye on new skill gaps as the venture grows into its next stage."},
        1: {"title": "You have a partial team.", "why_it_matters": "Most ventures start with a partial team — the key is knowing exactly which gap to close first.", "next_step": "Identify the one skill most blocking your next milestone and address that first."},
    },
    "competitive_differentiation": {
        2: {"title": "Your differentiation is clear and defensible.", "why_it_matters": "Clear differentiation is what stops a venture from competing purely on price.", "next_step": "Keep validating that this differentiation still matters as competitors evolve."},
        1: {"title": "You have some differentiation.", "why_it_matters": "Some differentiation is a start; sharpening it against your closest real alternatives makes the case much stronger.", "next_step": "Compare directly against the 2-3 closest alternatives on the one dimension customers say matters most."},
    },
}

# Illustrative, non-fabricated examples shown alongside the coaching text — the same style as the
# vision's own samples ("We'll help you discover the right pricing after validating customer
# willingness to pay.").
_EXAMPLE_BY_DIMENSION: dict[str, str] = {
    "problem_clarity": "\"[Segment] loses/wastes [specific cost] because [problem].\"",
    "customer_pain_evidence": "\"Tell me about the last time you dealt with this — what did you do?\"",
    "market_size_evidence": "Start with one well-defined niche rather than a broad market claim.",
    "product_maturity": "A manual or lightly-automated first version, proven on one real case.",
    "traction": "One signed pilot letter of intent is worth more than a hundred sign-up-page visits.",
    "revenue_model_clarity": "Try a simple per-seat or per-location monthly price to start.",
    "team_completeness": "A part-time advisor can often cover a gap faster than a full-time hire.",
    "competitive_differentiation": "Name the one thing customers would miss most if you disappeared.",
}


_CATEGORY_URGENCY: dict[str, int] = {
    "confirmed_risk": 3,
    "validation_opportunity": 2,
    "discovery_question": 2,
    "improvement_opportunity": 1,
    "future_enhancement": 1,
    "strength": 0,
}


def score_item(category: str, weight: float) -> float:
    """Public so callers merging in non-rubric items (e.g. capability-library-derived guidance in
    app.agents.mentor_synthesis) can rank them on the exact same scale, keeping one single
    prioritized ordering across the whole product instead of several independently-computed ones.
    """
    return _CATEGORY_URGENCY.get(category, 0) * 100 + weight * 100


def finalize_priority(items: list[dict], *, strip_internal: bool = False) -> list[dict]:
    """Sort a combined list of guidance items (rubric-derived and/or capability-derived) by
    `score_item` and return new dicts with 1-indexed `priority` assigned — never mutates the input
    items, so the same source list (e.g. a judge_summary already persisted/shared elsewhere) can be
    safely re-ranked more than once. Every item must carry an internal `_weight` field (rubric items
    already do; capability-derived items should set one, 0.0 if none applies). Pass
    `strip_internal=True` once, at the point the final merged list is built for API/frontend
    consumption, to drop the internal `_weight` field.
    """
    ordered = sorted(items, key=lambda i: (-score_item(i["category"], i.get("_weight", 0.0)), i["dimension"]))
    result = []
    for index, item in enumerate(ordered, start=1):
        copied = dict(item)
        copied["priority"] = index
        if strip_internal:
            copied.pop("_weight", None)
        result.append(copied)
    return result


def _category_for(state: str, severity: int | None, dimension: str) -> str | None:
    if state == "confirmed_positive":
        return "strength" if severity == 2 else "improvement_opportunity"
    if state == "not_sure_yet":
        return "discovery_question"
    if state == "confirmed_negative":
        return _NEGATIVE_CATEGORY.get(dimension, "validation_opportunity")
    return None  # not_applicable — excluded entirely


_EARLY_STAGE_KEYWORDS = ("idea", "unspecified")


def _build_item(breakdown_item: dict, stage: str | None) -> dict | None:
    dimension = breakdown_item["dimension"]
    state = breakdown_item["state"]
    severity = breakdown_item.get("raw_score")
    category = _category_for(state, severity, dimension)
    if category is None:
        return None

    if category in ("strength", "improvement_opportunity") and state == "confirmed_positive":
        content = _POSITIVE_CONTENT[dimension][severity]
        title, why_it_matters, next_step = content["title"], content["why_it_matters"], content["next_step"]
    else:
        hyp = build_hypothesis(dimension)
        title = {
            "discovery_question": f"{breakdown_item['label']} is a discovery question, not a weakness.",
            "validation_opportunity": f"{breakdown_item['label']} is your next validation opportunity.",
        }.get(category, f"{breakdown_item['label']} needs attention.")
        why_it_matters = hyp["starting_hypothesis"]
        next_step = hyp["validation_task"]
        is_early_stage = not stage or any(kw in stage.lower() for kw in _EARLY_STAGE_KEYWORDS)
        if category in ("discovery_question", "validation_opportunity") and is_early_stage:
            why_it_matters += " This is completely normal at this early a stage — it isn't a flaw in the idea."

    return {
        "dimension": dimension,
        "category": category,
        "status": _STATUS_BY_CATEGORY[category],
        "title": title,
        "observation": breakdown_item["scale_description"],
        "why_it_matters": why_it_matters,
        "next_step": next_step,
        "example": _EXAMPLE_BY_DIMENSION.get(dimension, next_step),
        "priority": 0,  # assigned by finalize_priority
        "evidence_state": state,
        "source": "deterministic",
        "_weight": breakdown_item.get("weight", 0.0),
    }


def build_founder_guidance_items(funding_assessment: dict, market_evidence: dict | None = None) -> list[dict]:
    """Build one structured guidance item per applicable funding-readiness dimension (excludes
    `not_applicable`). Priority is assigned relative to these rubric items only — see
    `finalize_priority` for re-ranking once app.agents.mentor_synthesis merges in
    capability-derived items; call it again with `strip_internal=True` on the final merged list.

    `market_evidence.startup_stage` (if supplied) only ever softens coaching language for an
    early-stage venture — it never changes a dimension's assigned category (see
    `_NEGATIVE_CATEGORY`).
    """
    stage = (market_evidence or {}).get("startup_stage")
    items = [
        item
        for item in (_build_item(b, stage) for b in funding_assessment.get("breakdown", []))
        if item is not None
    ]
    return finalize_priority(items)
