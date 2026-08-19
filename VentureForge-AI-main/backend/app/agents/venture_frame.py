"""Structured Venture Frame — VentureForge Intelligence Architecture, Phase B.

One canonical, structured understanding of a venture, assembled from data every upstream module in
this pipeline has already computed (the industry classifier, venture-positioning resolution, market
evidence, the business-model agent, the funding-readiness rubric, competitor analysis, and the
Evidence Ledger's confidence priors from Phase A). This module extracts no new information from raw
text and calls no LLM — it is a read-only aggregation layer, not a new source of intelligence, built
so later phases can reason from one shared "mental model" of the venture instead of each
re-deriving the same concepts independently (see the module-level audit note below).

Every field is either:
  - a `FrameField` — `{value, confidence, evidence_ids, supporting_text, origin}`, where `value` is
    `None` ("Unknown") whenever no upstream module produced real evidence for it — never guessed,
    never optimistically filled; or
  - a `HypothesisField` — `{primary, secondary, is_ambiguous, reason}` for the two concepts
    (industry, positioning) where the pipeline already tracks more than one live candidate, so
    ambiguity is represented rather than collapsed into a single answer. This directly reuses
    `venture_positioning`'s existing `secondary_domains`/`is_low_confidence` and the industry
    classifier's existing `alternatives` list — no new ambiguity-detection logic is introduced
    here; it is prepared, not implemented, for a future Hypothesis Set phase.

Confidence numbers here reuse `app.agents.evidence_ledger.SOURCE_TYPE_BASE_CONFIDENCE` — the same
disclosed priors Phase A already established — rather than inventing a second, parallel set of
confidence constants. The one exception is each `HypothesisField`'s own confidence, which is
deliberately the upstream model's *own reported* confidence (e.g. the industry classifier's
`confidence`, the taxonomy's `weighted_score`), since a hypothesis's job is to represent how
confident its *source* is, not how much the ledger's evidence-combination formula would discount
it — these are two different questions serving two different consumers.

The one genuinely new computation performed here (not merely re-read) is a single call to
`app.agents.regulatory_context.classify_regulatory_context` — the exact function
`mentor_synthesis.py` and `strategic_opportunity.py` already call independently later in the
pipeline. Reusing that function here (rather than reimplementing its keyword logic) means the
Venture Frame's `regulatory_context` field is never a second, divergent implementation of the same
classification — see "Audit: re-parsing found" below for why this is called out explicitly.

Audit: re-parsing found (Phase B, task FIRST). `startup_description` is independently re-parsed by
at least four modules today: the industry classifier (`app.ml.predictor`, statistical), the
positioning taxonomy (`app.ml.positioning_taxonomy`, keyword/phrase matching), the capability
library (`app.ml.capability_library`, substring matching), and `regulatory_context` (keyword +
negation matching). Phase B does not change any of those four modules' internals or their inputs —
doing so would mean rewiring `capability_library`/`regulatory_context` to consume this frame instead
of raw text, which is a larger, riskier change than "additive only, no breaking changes" permits and
belongs to a later phase's scope, not this one. What Phase B *does* fix today: it stops downstream
consumers of *this* frame from separately re-deriving concepts like "primary domain," "customer,"
or "venture stage" in their own words — they can now read one canonical, evidence-linked answer
instead. The one call this module makes to `classify_regulatory_context` is additional (a third
call to that specific function, alongside its existing two call sites) but not duplicative — it
calls the exact same, already-existing, pure function rather than reimplementing its logic, and the
extra call is cheap keyword matching with no side effects.

Adaptations from the originally suggested field list, and why: "Buyer" and "Primary User" are not
represented as two separate fields — the current schema (`market_evidence.customer_type`) only ever
captures one such concept, and inventing a distinction the evidence doesn't support would violate
the "no guessing" requirement more than it would help. The same applies to "Founder Stage" vs.
"Market Stage" (both collapse to the single `market_evidence.startup_stage` the founder actually
answered) and to "Product Type"/"Technology" (no dedicated classifier produces either today — adding
placeholder fields that are always `Unknown` for every venture would add noise, not information;
they are intentionally omitted rather than stubbed out). "Key Assumptions," "Dependencies,"
"Primary Risks" beyond the one regulatory constraint, and a fully general "Known Unknowns" beyond
`open_questions` are reserved for the Causal Reasoning and Decision Synthesis phases, which have the
actual mechanism (cross-module rules) to populate them honestly — stubbing them out now with no real
content would be exactly the "generic filler" failure mode this whole architecture exists to avoid.

The returned dict is deep-copied before being returned and must be treated as immutable by every
consumer: later phases (Hypothesis Set, Decision Synthesis, ...) may read from and reference a
Venture Frame, and may build new *annotations* alongside it, but must never mutate the dict returned
here in place. Python offers no zero-cost enforced immutability for nested dicts without introducing
a pattern not used anywhere else in this codebase, so the practical guarantee this phase provides is:
(a) the frame never aliases a mutable object from its inputs, so mutating the frame can never
corrupt upstream state and vice versa, and (b) `build_venture_frame` is deterministic — identical
inputs always produce an equal (not merely similar) output — which is directly tested.
"""

from __future__ import annotations

import copy
from typing import TypedDict

from app.agents.evidence_ledger import SOURCE_TYPE_BASE_CONFIDENCE
from app.agents.regulatory_context import classify_regulatory_context

VENTURE_FRAME_VERSION = "v1"

_CONFIRMED = SOURCE_TYPE_BASE_CONFIDENCE["user_confirmed"]

# `classify_regulatory_context`'s keyword/negation match is a deterministic rule, not a founder
# confirmation or a statistical model — it doesn't yet map cleanly onto any of Phase A's three
# source types, so it gets its own disclosed constant rather than silently reusing "user_confirmed"
# (which would overstate it) or "model_inference" (which would understate a rule that is, unlike a
# statistical prediction, always either exactly right or exactly wrong given its keyword list).
# Revisit once the Evidence Ledger's source-type taxonomy is next extended with a dedicated
# "deterministic_rule" category.
REGULATORY_RULE_CONFIDENCE = 0.6


class FrameField(TypedDict):
    value: object
    confidence: float
    evidence_ids: list[str]
    supporting_text: str | None
    origin: str


class HypothesisField(TypedDict):
    primary: FrameField
    secondary: FrameField | None
    is_ambiguous: bool
    reason: str | None


def is_known(field: FrameField) -> bool:
    """True if a `FrameField` carries a real value rather than an honest Unknown."""
    return field["value"] is not None


def _unknown(origin: str) -> FrameField:
    return {"value": None, "confidence": 0.0, "evidence_ids": [], "supporting_text": None, "origin": origin}


def _field(value: object, confidence: float, evidence_ids: list[str], supporting_text: str | None, origin: str) -> FrameField:
    if value in (None, "", "unknown", []):
        return _unknown(origin)
    return {
        "value": value,
        "confidence": round(float(confidence), 4),
        "evidence_ids": list(evidence_ids),
        "supporting_text": supporting_text,
        "origin": origin,
    }


def _industry_hypothesis(industry_prediction: dict | None) -> HypothesisField:
    if not industry_prediction:
        return {
            "primary": _unknown("industry_classifier"),
            "secondary": None,
            "is_ambiguous": False,
            "reason": "No industry prediction was produced for this run.",
        }

    reported_confidence = industry_prediction.get("confidence", 0.0)
    primary = _field(
        industry_prediction.get("predicted_industry"),
        reported_confidence,
        ["model:industry_prediction"],
        f"Industry classifier prediction (model-reported confidence {reported_confidence:.2f}).",
        "industry_classifier",
    )
    alternatives = industry_prediction.get("alternatives") or []
    secondary = None
    if alternatives:
        top_alt = alternatives[0]
        secondary = _field(
            top_alt.get("industry"),
            top_alt.get("confidence", 0.0),
            ["model:industry_prediction"],
            "Next-ranked industry-classifier alternative.",
            "industry_classifier",
        )
    is_ambiguous = bool(industry_prediction.get("is_uncertain"))
    reason = (
        "The industry classifier flagged this prediction as uncertain — held open as a hypothesis "
        "alongside the next-ranked alternative, not collapsed to a single certain answer."
        if is_ambiguous
        else None
    )
    return {"primary": primary, "secondary": secondary, "is_ambiguous": is_ambiguous, "reason": reason}


def _positioning_hypothesis(venture_positioning: dict | None) -> HypothesisField:
    if not venture_positioning:
        return {
            "primary": _unknown("venture_positioning"),
            "secondary": None,
            "is_ambiguous": False,
            "reason": "Venture positioning was not resolved for this run.",
        }

    resolution_source = venture_positioning.get("resolution_source", "unknown")
    primary = _field(
        venture_positioning.get("primary_domain"),
        venture_positioning.get("confidence", 0.0),
        ["model:venture_positioning"],
        f"Resolved via '{resolution_source}' against the controlled taxonomy.",
        "venture_positioning",
    )
    secondary_domains = venture_positioning.get("secondary_domains") or []
    secondary = None
    if secondary_domains:
        secondary = _field(
            secondary_domains[0],
            venture_positioning.get("confidence", 0.0),
            ["model:venture_positioning"],
            "Next-ranked taxonomy candidate.",
            "venture_positioning",
        )
    is_ambiguous = bool(venture_positioning.get("is_low_confidence"))
    reason = (
        "Venture positioning was flagged low-confidence — held open as a hypothesis alongside the "
        "next-ranked taxonomy candidate, not collapsed to a single certain answer."
        if is_ambiguous
        else None
    )
    return {"primary": primary, "secondary": secondary, "is_ambiguous": is_ambiguous, "reason": reason}


_MARKET_EVIDENCE_LABELS: dict[str, str] = {
    "customer_type": "buyer/user",
    "target_market": "target market",
    "startup_stage": "venture stage",
    "geography": "geography",
}


def _market_evidence_field(market_evidence: dict | None, field: str) -> FrameField:
    value = (market_evidence or {}).get(field)
    label = _MARKET_EVIDENCE_LABELS[field]
    origin = f"market_evidence.{field}"
    if not value:
        return _unknown(origin)
    return _field(value, _CONFIRMED, [f"market_evidence:{field}"], f"Founder-stated {label}.", origin)


def _rubric_dimension_field(funding_assessment: dict | None, dimension: str) -> FrameField:
    """Both `confirmed_positive` and `confirmed_negative` are direct founder confirmations (the
    same `user_confirmed` classification `app.agents.evidence_ledger` already uses for this rubric
    state) — only `not_sure_yet`/`not_applicable`/a missing entry are represented as Unknown here.
    """
    origin = f"funding_readiness.{dimension}"
    breakdown = {b["dimension"]: b for b in (funding_assessment or {}).get("breakdown", [])}
    entry = breakdown.get(dimension)
    if not entry or entry.get("state") not in ("confirmed_positive", "confirmed_negative"):
        return _unknown(origin)
    return _field(
        entry["scale_description"], _CONFIRMED, [f"rubric:{dimension}"],
        f"{entry['label']} rubric answer.", origin,
    )


def _core_venture_summary_field(business_model: dict | None) -> FrameField:
    origin = "business_model_agent.value_proposition"
    value = (business_model or {}).get("value_proposition")
    if not value or value == "unknown":
        return _unknown(origin)
    return _field(
        value, _CONFIRMED, [],
        "Extractive first sentence of the founder's own description — quoted, not invented.", origin,
    )


def _competition_field(competitor_analysis: dict | None) -> FrameField:
    origin = "competitor_agent.verified_competitors"
    verified = (competitor_analysis or {}).get("verified_competitors") or []
    if not verified:
        return _unknown(origin)
    return _field(
        verified, _CONFIRMED, ["market_evidence:known_competitors"],
        "Competitors the founder named directly — never a verified company database.", origin,
    )


def _deployment_context_field(venture_positioning: dict | None) -> FrameField:
    origin = "venture_positioning.deployment_sectors"
    sectors = (venture_positioning or {}).get("deployment_sectors") or []
    if not sectors:
        return _unknown(origin)
    return _field(
        sectors, (venture_positioning or {}).get("confidence", 0.0), ["model:venture_positioning"],
        "Deployment sectors resolved by venture positioning.", origin,
    )


def _regulatory_context_field(startup_description: str, venture_positioning: dict | None) -> FrameField:
    """Reuses `app.agents.regulatory_context.classify_regulatory_context` directly — the same
    function `mentor_synthesis.py`/`strategic_opportunity.py` already call — rather than
    reimplementing its keyword/negation logic a second time. See module docstring's audit note."""
    origin = "regulatory_context"
    primary_domain = (venture_positioning or {}).get("primary_domain")
    deployment_sectors = (venture_positioning or {}).get("deployment_sectors")
    result = classify_regulatory_context(startup_description or "", primary_domain, deployment_sectors)
    if result is None:
        return _unknown(origin)
    return _field(result["headline"], REGULATORY_RULE_CONFIDENCE, [], result["note"], origin)


def _open_questions(funding_assessment: dict | None) -> list[str]:
    breakdown = {b["dimension"]: b for b in (funding_assessment or {}).get("breakdown", [])}
    return [
        breakdown[dim]["label"]
        for dim in (funding_assessment or {}).get("missing_evidence", [])
        if dim in breakdown
    ]


def build_venture_frame(
    startup_name: str = "",
    startup_description: str = "",
    funding_assessment: dict | None = None,
    industry_prediction: dict | None = None,
    venture_positioning: dict | None = None,
    market_evidence: dict | None = None,
    business_model: dict | None = None,
    competitor_analysis: dict | None = None,
) -> dict:
    """Assemble the Venture Frame for one analysis run. Purely additive and read-only: nothing
    produced upstream is changed by calling this, and this function has no side effects.
    Deterministic and idempotent — identical inputs always produce an equal output.
    """
    regulatory_field = _regulatory_context_field(startup_description, venture_positioning)

    frame = {
        "venture_frame_version": VENTURE_FRAME_VERSION,
        "startup_name": startup_name or None,
        "core_venture_summary": _core_venture_summary_field(business_model),
        "industry": _industry_hypothesis(industry_prediction),
        "positioning": _positioning_hypothesis(venture_positioning),
        "customer": _market_evidence_field(market_evidence, "customer_type"),
        "target_market": _market_evidence_field(market_evidence, "target_market"),
        "venture_stage": _market_evidence_field(market_evidence, "startup_stage"),
        "geography": _market_evidence_field(market_evidence, "geography"),
        "deployment_context": _deployment_context_field(venture_positioning),
        "revenue_model": _rubric_dimension_field(funding_assessment, "revenue_model_clarity"),
        "competition": _competition_field(competitor_analysis),
        "differentiation": _rubric_dimension_field(funding_assessment, "competitive_differentiation"),
        "regulatory_context": regulatory_field,
        "open_questions": _open_questions(funding_assessment),
        "known_constraints": [regulatory_field] if is_known(regulatory_field) else [],
    }
    # Deep-copied so the returned frame never aliases a mutable object from its inputs (or from any
    # nested list/dict built above) — mutating the frame afterward can never corrupt upstream state,
    # and vice versa. See module docstring's immutability note.
    return copy.deepcopy(frame)
