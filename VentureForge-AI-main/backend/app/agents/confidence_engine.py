"""The Confidence Engine — VentureForge Intelligence Architecture, Phase D.

The single, canonical implementation of every piece of *evidence-confidence* math in this
pipeline. Phase A (`evidence_ledger.py`) introduced the first version of this math
(`SOURCE_TYPE_BASE_CONFIDENCE`, `combine_confidence`) directly inside the Evidence Ledger module;
Phase D moves that implementation here and has `evidence_ledger.py` import it back, so there is
exactly one place in the codebase that defines how confidence numbers are computed and combined —
every other module either reads a confidence value already computed elsewhere, or calls into this
module. See the module-level audit report (delivered alongside this phase) for the full inventory
of every confidence/certainty/probability-like computation found in the repository and why each was
kept, merged into this engine, or documented as a deliberately distinct concept.

Three distinct concepts, kept explicitly separate (per the architecture's own instruction — do not
conflate "confidence" with "probability"):

  - **Evidence confidence** (this module, `combine_confidence`): how much a specific claim should
    be trusted, given the evidence backing it. Always in [0, 1]. This is what Phase A/B/C already
    use throughout the Evidence Ledger, Venture Frame, and Hypothesis Set.
  - **Prediction probability** (untouched, lives in `app.ml.predictor`/`app.ml.success_predictor`):
    a trained model's own calibrated output probability. This engine never recomputes a model's
    probability — it only *discounts* a model's reported confidence when treating it as evidence
    (see `SOURCE_TYPE_BASE_CONFIDENCE["model_inference"]`/`MODEL_INFERENCE_DISCOUNT`, both already
    established in Phase A and re-exported unchanged from here).
  - **Recommendation certainty / epistemic tier** (untouched, lives in `app.ai.schemas`'
    `confidence_tier` enums used by `idea_expansion.py`/`strategic_opportunity.py`): a categorical
    tag distinguishing a confirmed fact from a speculative hypothesis — not a numeric score at all,
    and structurally incapable of being merged into a [0, 1] confidence number without losing its
    actual meaning. Left exactly as-is.

Confidence propagation (new in Phase D): `propagate_confidence` implements the rule a downstream
conclusion (a Hypothesis built from a Frame field, or — in a future phase — a Decision built from a
Hypothesis) may never be more confident than its least-confident required input, with a small bonus
only when multiple independent inputs agree. This is the literal mechanism by which "if evidence
changes, every downstream confidence automatically changes" becomes true by construction: any
downstream computation that calls `propagate_confidence(*upstream_values)` inherits upstream
changes automatically, rather than needing to be manually kept in sync with them.
"""

from __future__ import annotations

from typing import Literal, TypedDict

CONFIDENCE_ENGINE_VERSION = "v1"

# --- Evidence confidence (moved here from app.agents.evidence_ledger, Phase A) -------------------

# Disclosed, fixed base-confidence priors per source type. Not learned — no outcome data exists yet
# to learn them from. Each is a considered, documented judgment call, not an arbitrary number:
#   - user_confirmed: the founder directly answered a question (positive or negative) — the
#     highest-trust source available to this system, since it is a direct, attributable statement.
#   - user_not_sure: an explicit "not sure yet" is itself weak positive information (the founder
#     engaged with the question) — deliberately not zero.
#   - model_inference: anything the pipeline inferred rather than was told (e.g. the industry
#     classifier's predicted label) always costs confidence relative to being told directly,
#     regardless of how confident the model itself reports being — see MODEL_INFERENCE_DISCOUNT.
#   - retrieved_comparable / model_extraction: reserved for future phases (retrieval integration,
#     Structured Venture Frame extraction) — no evidence items of these types are produced yet.
SOURCE_TYPE_BASE_CONFIDENCE: dict[str, float] = {
    "user_confirmed": 0.9,
    "user_not_sure": 0.3,
    "model_inference": 0.4,
}

# A model's own reported confidence is discounted by this factor before entering the ledger,
# because inference is structurally less trustworthy than direct confirmation regardless of how
# confident the model claims to be — see SOURCE_TYPE_BASE_CONFIDENCE's "model_inference" note.
MODEL_INFERENCE_DISCOUNT = 0.5


class ConfidenceItem(TypedDict):
    """The minimal shape `combine_confidence` needs from an evidence-bearing item — a structural
    subset of `app.agents.evidence_ledger.EvidenceItem`, so any module (not only the Evidence
    Ledger) can combine confidences without depending on the Ledger's full item shape."""

    source_type: str
    base_confidence: float


def combine_confidence(items: list[ConfidenceItem]) -> float:
    """Combine a set of evidence items into one confidence value in [0, 1].

    Independent source types combine via a noisy-OR rule with diminishing returns
    (`1 - prod(1 - c_i)`), so several independent kinds of corroboration raise confidence more than
    any single one alone, but corroboration alone never reaches certainty. Multiple items of the
    *same* source type are first collapsed to their max (never summed or averaged) before combining
    across types, so repeating the same kind of evidence cannot fake the effect of genuinely
    independent corroboration.

    This function does not yet penalize contradiction (each item's `contradicts` field, where
    present, is not consulted here) — that is Phase E's (Contradiction Detection) responsibility;
    today every caller combines purely corroborating evidence.
    """
    if not items:
        return 0.0
    by_source_type: dict[str, float] = {}
    for item in items:
        source_type = item["source_type"]
        by_source_type[source_type] = max(by_source_type.get(source_type, 0.0), item["base_confidence"])
    product_of_complements = 1.0
    for confidence in by_source_type.values():
        product_of_complements *= 1.0 - confidence
    return round(1.0 - product_of_complements, 4)


# --- Confidence propagation (new in Phase D) -----------------------------------------------------

# The bonus applied when >=2 independent upstream confidences agree (see `propagate_confidence`).
# Disclosed and small by design: propagation must never let a downstream conclusion exceed what its
# weakest required input would alone justify by more than a modest margin — the bonus rewards
# genuine multi-input agreement without letting it manufacture certainty no single input has.
_PROPAGATION_AGREEMENT_BONUS = 0.05


def propagate_confidence(*upstream: float) -> float:
    """A downstream conclusion's confidence, given the confidences of everything it necessarily
    depends on. Implements the rule: a conclusion can never be more confident than its
    least-confident required input (the `min` below), with a small, capped bonus when more than one
    independent upstream input agrees (i.e. all upstream values are reasonably close together,
    meaning they're reinforcing rather than merely coexisting).

    This is deliberately simple and disclosed rather than a fitted/learned function — no outcome
    data exists yet to fit one against (see the architecture document's rationale for why a learned
    Bayesian network is premature). `min()` is the one part of this rule that is not a judgment call
    at all: it is a strict mathematical requirement — a conclusion that depends on N premises is, at
    best, only as reliable as the weakest premise it depends on.

    Returns 0.0 for no arguments (an honest "no upstream confidence to propagate from"), and the
    single value unchanged for exactly one argument (nothing to agree or disagree with).
    """
    if not upstream:
        return 0.0
    if len(upstream) == 1:
        return round(upstream[0], 4)
    base = min(upstream)
    spread = max(upstream) - min(upstream)
    # Only reward agreement when upstream values are actually close together (spread <= 0.2) —
    # widely disagreeing upstream inputs are not "reinforcing," and must not receive a bonus.
    bonus = _PROPAGATION_AGREEMENT_BONUS if spread <= 0.2 else 0.0
    return round(min(1.0, base + bonus), 4)


# --- Shared status labeling (new in Phase D) ------------------------------------------------------

ConfidenceLabel = Literal["low", "medium", "high"]

# Disclosed thresholds for mapping a continuous confidence value to a 3-way label. Reused by every
# module in the pipeline that needs to present a low/medium/high label — replacing what were
# previously several independently-chosen thresholds (see the Phase D audit report for the exact
# list of call sites this replaces).
_HIGH_THRESHOLD = 0.6
_MEDIUM_THRESHOLD = 0.3


def label_confidence(value: float) -> ConfidenceLabel:
    """Map a [0, 1] confidence value to the shared low/medium/high label. This is the one place in
    the codebase that decides these cutoffs — see `_HIGH_THRESHOLD`/`_MEDIUM_THRESHOLD` above."""
    if value >= _HIGH_THRESHOLD:
        return "high"
    if value >= _MEDIUM_THRESHOLD:
        return "medium"
    return "low"
