"""Deterministic Hypothesis Engine (prototype).

For every `not_sure_yet` evidence gap, produces a structured hypothesis object instead of a bare
gap message — the deterministic engine that feeds `suggested_possibilities` in the Mentor output,
whether or not Gemini is configured. Domain-aware where a specific entry exists for the resolved
`primary_domain`; falls back to a generic, still-real (not fabricated) template otherwise.
"""

from __future__ import annotations

# Generic fallback hypothesis per funding-readiness dimension, used when no domain-specific entry
# below applies. Every entry is a real, defensible starting point — never a fabricated fact.
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

# Domain-specific overrides — only added where a specific, defensible hypothesis genuinely differs
# from the generic one. Keyed by (primary_domain, dimension).
_DOMAIN_OVERRIDES: dict[tuple[str, str], dict] = {
    ("Smart Facilities Technology", "revenue_model_clarity"): {
        "starting_hypothesis": "A one-time hardware/install fee plus a monthly per-building "
        "monitoring subscription — facilities buyers tend to prefer OpEx software spend over "
        "CapEx.",
        "assumptions": ["Hardware is a one-time cost; ongoing monitoring is the recurring value."],
        "alternatives": ["Pure SaaS licensing onto existing sensors", "Per-square-foot pricing"],
        "validation_task": "Price both a hardware-plus-subscription and a pure-SaaS model to 3 "
        "facilities managers and compare stated willingness to pay.",
    },
    ("Clinical Decision Support", "revenue_model_clarity"): {
        "starting_hypothesis": "Institutional sale to a clinic or hospital system, priced per "
        "patient monitored per month, rather than a direct-to-consumer product.",
        "assumptions": ["The buyer is the institution, not the individual patient."],
        "alternatives": ["Per-institution flat licensing"],
        "validation_task": "Interview one clinic or hospital department on how they would budget "
        "for this before assuming a price point.",
    },
    ("Restaurant Operations Technology", "revenue_model_clarity"): {
        "starting_hypothesis": "A flat monthly SaaS fee per location, priced low enough to sit "
        "comfortably next to existing POS software costs.",
        "assumptions": ["Independent restaurants are price-sensitive on new software."],
        "alternatives": ["Revenue-share on measured waste savings"],
        "validation_task": "Price both models to 3 independent restaurant owners and compare "
        "reactions.",
    },
}


def build_hypothesis(dimension: str, primary_domain: str) -> dict:
    override = _DOMAIN_OVERRIDES.get((primary_domain, dimension))
    if override:
        return {"dimension": dimension, **override}
    generic = _GENERIC_HYPOTHESES.get(dimension)
    if generic:
        return {"dimension": dimension, **generic}
    return {
        "dimension": dimension,
        "starting_hypothesis": "Not enough is known yet to propose a specific starting hypothesis "
        "for this dimension.",
        "assumptions": [],
        "alternatives": [],
        "validation_task": f"Gather direct evidence for '{dimension}' before assuming an answer.",
    }


def build_hypotheses_for_gaps(not_sure_yet_dimensions: list[str], primary_domain: str) -> list[dict]:
    return [build_hypothesis(dim, primary_domain) for dim in not_sure_yet_dimensions]
