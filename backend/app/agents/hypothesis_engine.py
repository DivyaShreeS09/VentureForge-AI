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
        "starting_hypothesis": "A price is only a hypothesis until it's anchored to something the "
        "customer already feels. The real question isn't 'will they pay this amount' — it's what "
        "problem is painful enough that this amount feels cheap by comparison. A simple recurring "
        "subscription priced per customer or per location is a reasonable starting structure, but "
        "the number itself should come from evidence, not a guess.",
        "assumptions": ["Customers prefer predictable recurring pricing over one-off fees."],
        "alternatives": ["Usage-based pricing", "A free tier with a paid upgrade"],
        "validation_task": "Before finalizing a price, measure what it's actually replacing — time "
        "saved, money saved, waste reduced, or manual effort eliminated. Once that number is real, "
        "price 3 prospective customers on it and compare reactions.",
    },
    "market_size_evidence": {
        "starting_hypothesis": "The opportunity here isn't just the single segment you named — it's "
        "the broader pattern of replacing a manual, repetitive process with a predictable digital "
        "workflow. That pattern often extends to adjacent, operationally similar buyers later. "
        "Don't build for those yet; assume a narrow, well-defined initial segment until a sourced "
        "estimate exists, but keep the architecture flexible enough that expansion stays easy.",
        "assumptions": ["A credible initial market is smaller than the eventual addressable one."],
        "alternatives": ["A regional pilot market", "A single vertical within the broader space"],
        "validation_task": "Produce a sourced TAM/SAM/SOM estimate from public data before citing "
        "a market size.",
    },
    "traction": {
        "starting_hypothesis": "You've already proven you can build the product — that's no longer "
        "the risk. The uncertainty has shifted from engineering to customer behavior: until "
        "{buyer_noun} uses this repeatedly, every pricing, revenue, and growth assumption stays a "
        "hypothesis, not a fact. That's why another month of features is likely worth less right "
        "now than one week running a real {pilot_noun}.",
        "assumptions": ["Early traction is easier to earn in a narrow, motivated group first."],
        "alternatives": ["A paid pilot", "A free pilot in exchange for feedback rights"],
        "validation_task": "Pause feature work. Secure one concrete commitment from {buyer_noun} (a "
        "letter of intent or a signed trial) — then let real usage, not your own instinct, decide "
        "what to build next.",
    },
    "competitive_differentiation": {
        "starting_hypothesis": "Imagine a competitor copies every feature you've built by tomorrow — "
        "would customers still choose you? Right now the honest answer is probably not: your edge "
        "today is in the execution, not yet in anything structurally hard to replicate. A real moat "
        "is usually built in stages — pilot data, then usage analytics, then predictive insight, "
        "then benchmarking against peers — each stage raising the cost of switching away.",
        "assumptions": ["Existing alternatives are broader and less tailored to this specific case."],
        "alternatives": ["Differentiate on speed/simplicity", "Differentiate on a specific vertical"],
        "validation_task": "Name the one thing that gets harder to copy as you get more customers "
        "(data, workflow lock-in, a relationship) — then compare directly against the 2-3 closest "
        "real alternatives on exactly that dimension, not on feature count.",
    },
    "product_maturity": {
        "starting_hypothesis": "A manual or lightly-automated first version, proven on one real "
        "case, de-risks the idea faster than a fully built product.",
        "assumptions": ["The core value can be demonstrated without full automation."],
        "alternatives": ["A concierge/manual MVP", "A narrow single-feature prototype"],
        "validation_task": "Run the manual version with {buyer_noun} before investing in "
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
        "starting_hypothesis": "Don't ask whether someone would use this — almost everyone says yes "
        "to a friendly hypothetical. Ask what they use today, what frustrates them about it, and "
        "what would actually happen if it disappeared tomorrow. Those answers reveal real buying "
        "behavior; a hypothetical only reveals politeness. Assume the pain is real but unconfirmed "
        "until that direct evidence exists.",
        "assumptions": ["The problem is common enough to find several affected people quickly."],
        "alternatives": [],
        "validation_task": "Interview 5 people in the target group — but ask about their current "
        "behavior and workarounds, not their opinion of your idea.",
    },
}


_DEFAULT_VOCAB = {"pilot_noun": "pilot site or user group", "buyer_noun": "a pilot customer"}


def build_hypothesis(dimension: str, vocab: dict[str, str] | None = None) -> dict:
    """Build the structured hypothesis for one `not_sure_yet` dimension. Every field is a
    suggestion (`suggestion_label: "possibility"`), never presented as a confirmed fact.

    `vocab` (see app.agents.venture_vocabulary.vocab_for) lets a small number of templates adapt
    their noun choice — "a clinical pilot" vs. "a field trial" vs. "an early-adopter test group" —
    to the venture's own category (Critical Fix #2/#5: adaptive, diverse recommendations). Optional
    and additive: omitting it reproduces the exact generic text this always produced.
    """
    spec = _GENERIC_HYPOTHESES.get(dimension)
    if spec is None:
        # Unrecognized dimension key (e.g. a future rubric dimension not yet templated here) — an
        # honest "not enough is known" placeholder, never a fabricated hypothesis.
        readable_dimension = dimension.replace("_", " ")
        spec = {
            "starting_hypothesis": (
                f"Not enough is known yet to offer a specific starting guess on {readable_dimension}."
            ),
            "assumptions": [],
            "alternatives": [],
            "validation_task": f"Go find real evidence on {readable_dimension} before assuming an answer either way.",
        }
    fill = {**_DEFAULT_VOCAB, **(vocab or {})}
    spec = {
        key: (value.format(**fill) if isinstance(value, str) else value)
        for key, value in spec.items()
    }
    return {
        "source_dimension": dimension,
        "suggestion_label": "possibility",
        **spec,
    }


def build_hypotheses_for_gaps(not_sure_yet_dimensions: list[str], vocab: dict[str, str] | None = None) -> list[dict]:
    """Build one structured hypothesis per `not_sure_yet` dimension, in the given order."""
    return [build_hypothesis(dimension, vocab) for dimension in not_sure_yet_dimensions]
