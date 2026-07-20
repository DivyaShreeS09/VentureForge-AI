"""Deterministic Hypothesis Engine (Phase 0).

For every funding-readiness dimension left in a `not_sure_yet` evidence state (see
app.ml.funding_readiness.EvidenceState), produces a structured hypothesis instead of a flat gap
message: a starting hypothesis to work from, the assumptions it rests on, real alternatives, and a
concrete validation task. This is the deterministic engine behind `suggested_possibilities` in the
Judge Agent's output (app.agents.judge.synthesize), whether or not an LLM is configured — nothing
here is fabricated per-input, every dimension maps to one fixed, versioned template.

Domain-specific hypothesis overrides (keyed by `venture_positioning.primary_domain`, prototyped in
ml/prototypes/mentor_prototype/hypothesis_engine.py) are Phase 0.5 work, once that field exists in
production — this module intentionally implements only the dimension-generic hypotheses.
"""

from __future__ import annotations

HYPOTHESIS_ENGINE_VERSION = "v1"

# One real, defensible starting point per funding-readiness dimension — never a fabricated fact,
# always labeled as a suggestion (see `build_hypothesis`'s `suggestion_label`).
_GENERIC_HYPOTHESES: dict[str, dict] = {
    "revenue_model_clarity": {
        "starting_hypothesis": "A simple recurring subscription priced per customer or per location "
        "is usually the safest starting point until real willingness-to-pay data exists.",
        "assumptions": ["Customers prefer predictable recurring pricing over one-off fees."],
        "alternatives": ["Usage-based pricing", "A free tier with a paid upgrade"],
        "validation_task": "Price the offering to 3 prospective customers and compare reactions "
        "before committing to a model.",
    },
    "market_size_evidence": {
        "starting_hypothesis": "Assume a narrow, well-defined initial segment rather than a broad "
        "market claim until a sourced estimate exists.",
        "assumptions": ["A credible initial market is smaller than the eventual addressable one."],
        "alternatives": ["A regional pilot market", "A single vertical within the broader space"],
        "validation_task": "Produce a sourced TAM/SAM/SOM estimate from public data before citing "
        "a market size.",
    },
    "traction": {
        "starting_hypothesis": "A single, well-chosen pilot site or user group is a stronger next "
        "step than broad launch.",
        "assumptions": ["Early traction is easier to earn in a narrow, motivated group first."],
        "alternatives": ["A paid pilot", "A free pilot in exchange for feedback rights"],
        "validation_task": "Secure one concrete pilot commitment (a letter of intent or a signed "
        "trial) before building further.",
    },
    "competitive_differentiation": {
        "starting_hypothesis": "Differentiation likely comes from a narrower, more specific focus "
        "than existing broader alternatives, not from a feature-count advantage.",
        "assumptions": ["Existing alternatives are broader and less tailored to this specific case."],
        "alternatives": ["Differentiate on speed/simplicity", "Differentiate on a specific vertical"],
        "validation_task": "Compare directly against the 2-3 closest real alternatives on the one "
        "dimension customers say matters most.",
    },
    "product_maturity": {
        "starting_hypothesis": "A manual or lightly-automated first version, proven on one real "
        "case, de-risks the idea faster than a fully built product.",
        "assumptions": ["The core value can be demonstrated without full automation."],
        "alternatives": ["A concierge/manual MVP", "A narrow single-feature prototype"],
        "validation_task": "Run the manual version with one real user/customer before investing in "
        "full automation.",
    },
    "team_completeness": {
        "starting_hypothesis": "The most urgent gap is usually whichever core skill blocks getting "
        "to a first real user fastest.",
        "assumptions": ["A single missing core skill is a bigger risk than general team size."],
        "alternatives": ["A part-time advisor", "A co-founder search focused on the specific gap"],
        "validation_task": "Identify the one skill most blocking the next milestone and address "
        "that first.",
    },
    "problem_clarity": {
        "starting_hypothesis": "State the problem as one sentence naming who has it and what it "
        "costs them, before refining anything else.",
        "assumptions": [],
        "alternatives": [],
        "validation_task": "Write and test a one-sentence problem statement with 3 people in the "
        "target group.",
    },
    "customer_pain_evidence": {
        "starting_hypothesis": "Assume the pain is real but unconfirmed until direct evidence "
        "exists — interviews are cheaper than building around a guess.",
        "assumptions": ["The problem is common enough to find several affected people quickly."],
        "alternatives": [],
        "validation_task": "Interview 5 people in the target group specifically about this pain "
        "point before designing a solution.",
    },
}


def build_hypothesis(dimension: str) -> dict:
    """Build the structured hypothesis for one `not_sure_yet` dimension. Every field is a
    suggestion (`suggestion_label: "possibility"`), never presented as a confirmed fact.
    """
    spec = _GENERIC_HYPOTHESES.get(dimension)
    if spec is None:
        # Unrecognized dimension key (e.g. a future rubric dimension not yet templated here) — an
        # honest "not enough is known" placeholder, never a fabricated hypothesis.
        spec = {
            "starting_hypothesis": "Not enough is known yet to propose a specific starting "
            "hypothesis for this dimension.",
            "assumptions": [],
            "alternatives": [],
            "validation_task": f"Gather direct evidence for '{dimension}' before assuming an answer.",
        }
    return {
        "source_dimension": dimension,
        "suggestion_label": "possibility",
        **spec,
    }


def build_hypotheses_for_gaps(not_sure_yet_dimensions: list[str]) -> list[dict]:
    """Build one structured hypothesis per `not_sure_yet` dimension, in the given order."""
    return [build_hypothesis(dimension) for dimension in not_sure_yet_dimensions]
