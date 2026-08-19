"""Hypothesis Set — VentureForge Intelligence Architecture, Phase C.

Builds multiple, explicitly competing interpretations of a venture from the Structured Venture
Frame (Phase B) and the Evidence Ledger (Phase A) — never from raw founder text, never from a new
parsing pass, and never from a second confidence system. Every hypothesis's confidence is either
copied directly from a `FrameField`/`EvidenceItem` already computed upstream, or combined via
`app.agents.evidence_ledger.combine_confidence` — the same noisy-OR formula Phase A already
established. This module introduces no new confidence arithmetic of its own.

Design principle: never fabricate a competing hypothesis where none exists. A category that only
has one real candidate (e.g. `target_customer`, where `market_evidence.customer_type` is a single
founder-supplied field with no second interpretation to weigh against) still gets exactly one
`Hypothesis` — a hypothesis set of size one is not a bug, it is the honest reflection of what the
evidence actually supports. A category with no supporting evidence at all is omitted entirely
rather than populated with an invented placeholder.

Categories NOT built, and why (deliberate, not an oversight):
  - "Go-to-market": no dedicated GTM evidence field exists anywhere in the Venture Frame, the
    Evidence Ledger, or the deterministic outputs available at this point in the pipeline. Phase
    B's own docstring reserves this content for a later phase (Decision Synthesis) that has the
    actual mechanism to populate it honestly; stubbing it out now would be the "generic filler"
    failure mode this architecture exists to avoid.
  - `market_intelligence`'s `opportunity_drivers`/`constraints` free-text lists are deliberately NOT
    used as a source for `major_opportunity`/`major_risk`: those strings carry no evidence-id
    linkage back to the Evidence Ledger, and inventing a link (or a second confidence number) for
    them would violate both "never hallucinate evidence" and "do not create a second confidence
    system." `major_opportunity`/`major_risk` are instead built only from funding-readiness rubric
    evidence and the Venture Frame's `regulatory_context` field, both of which already carry real
    evidence ids and ledger-derived confidence.

`industry_interpretation` treats the industry classifier's primary/secondary and venture-
positioning's primary/secondary as two independent signal sources that may *corroborate* (when they
name the same domain — merged via `combine_confidence`, a real confidence boost, not a new formula)
but are never automatically treated as *contradicting* each other merely for naming different
labels: the classifier (coarse, e.g. "healthcare") and the taxonomy (fine-grained, e.g. "Clinical
Decision Support") operate at different levels of resolution by design, and a difference in
specificity is not evidence of disagreement. Genuine competition (a resolver's primary vs. its own
secondary) is only represented when that resolver's own Phase B output already flagged itself
ambiguous (`is_ambiguous`) — never re-derived here.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from app.agents.evidence_ledger import combine_confidence
from app.agents.venture_frame import FrameField, HypothesisField, is_known

HYPOTHESIS_SET_VERSION = "v1"

Status = Literal["leading", "plausible", "weak", "rejected"]

# Status thresholds are a labeling scheme applied *to* an already-computed confidence number, not a
# second confidence system — the confidence itself always comes from evidence_ledger.combine_confidence
# or a FrameField's own confidence, never from these thresholds.
_PLAUSIBLE_THRESHOLD = 0.4


class Hypothesis(TypedDict):
    id: str
    category: str
    title: str
    explanation: str
    confidence: float
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    assumptions: list[str]
    what_would_strengthen: str
    what_would_weaken: str
    status: Status
    # Populated only for a category's single highest-confidence ("leading") hypothesis — the
    # explicit self-critique this architecture requires before a hypothesis may be presented as the
    # current best answer. `None` for every non-leading hypothesis.
    self_critique: dict | None


def _status_for(confidence: float, rank: int, supporting: list[str], contradicting: list[str]) -> Status:
    if len(contradicting) > len(supporting):
        return "rejected"
    if rank == 1:
        return "leading"
    if confidence >= _PLAUSIBLE_THRESHOLD:
        return "plausible"
    return "weak"


def _self_critique(supporting: list[str], contradicting: list[str], confidence: float) -> dict:
    return {
        "why_this_might_be_wrong": (
            f"This rests on {len(supporting)} piece(s) of evidence"
            + (f" and {len(contradicting)} contradicting piece(s)" if contradicting else "")
            + f" (combined confidence {confidence:.2f}) — not a certainty."
        ),
        "missing_evidence": (
            "No independent corroborating source yet — this comes from a single evidence item."
            if len(supporting) <= 1
            else "Additional independent corroboration would still strengthen this further."
        ),
        "experiment_to_resolve_uncertainty": (
            "Ask the founder directly to confirm or correct this claim, or request one additional "
            "independent piece of evidence specific to it."
        ),
    }


def _finalize_category(category: str, hyps: list[dict]) -> list[Hypothesis]:
    """Rank by confidence (desc), assign id/status/self_critique. Never mutates its input dicts."""
    ranked = sorted(hyps, key=lambda h: h["confidence"], reverse=True)
    result: list[Hypothesis] = []
    for rank, hyp in enumerate(ranked, start=1):
        supporting = hyp["supporting_evidence_ids"]
        contradicting = hyp["contradicting_evidence_ids"]
        status = _status_for(hyp["confidence"], rank, supporting, contradicting)
        result.append(
            {
                "id": f"{category}:{rank}",
                "category": category,
                "title": hyp["title"],
                "explanation": hyp["explanation"],
                "confidence": round(hyp["confidence"], 4),
                "supporting_evidence_ids": list(supporting),
                "contradicting_evidence_ids": list(contradicting),
                "assumptions": list(hyp["assumptions"]),
                "what_would_strengthen": hyp["what_would_strengthen"],
                "what_would_weaken": hyp["what_would_weaken"],
                "status": status,
                "self_critique": _self_critique(supporting, contradicting, hyp["confidence"]) if status == "leading" else None,
            }
        )
    return result


def _single_field_category(category: str, field: FrameField, explanation_prefix: str) -> list[Hypothesis]:
    if not is_known(field):
        return []
    hyp = {
        "title": str(field["value"]),
        "explanation": f"{explanation_prefix}: {field['supporting_text'] or field['value']}",
        "confidence": field["confidence"],
        "supporting_evidence_ids": list(field["evidence_ids"]),
        "contradicting_evidence_ids": [],
        "assumptions": [f"Assumes {field['origin']} remains accurate as the venture evolves."],
        "what_would_strengthen": "A second, independent piece of evidence confirming the same claim.",
        "what_would_weaken": "Founder or new evidence contradicting this claim.",
    }
    return _finalize_category(category, [hyp])


def _hypothesis_field_signals(resolver_name: str, hyp_field: HypothesisField) -> list[dict]:
    """Unfinalized hypothesis dicts (not yet ranked/id'd) for one resolver's primary/secondary
    candidates, so the caller can merge signals from more than one resolver into one category
    before finalizing."""
    primary = hyp_field["primary"]
    if not is_known(primary):
        return []
    hyps = [
        {
            "title": str(primary["value"]),
            "explanation": f"{resolver_name}'s top candidate: {primary['supporting_text']}",
            "confidence": primary["confidence"],
            "supporting_evidence_ids": list(primary["evidence_ids"]),
            "contradicting_evidence_ids": [],
            "assumptions": [f"Assumes {primary['origin']}'s prediction is representative of the full description."],
            "what_would_strengthen": "Independent corroboration from a second source (e.g. founder confirmation).",
            "what_would_weaken": "A materially different description that shifts the underlying prediction.",
        }
    ]
    secondary = hyp_field["secondary"]
    if hyp_field["is_ambiguous"] and secondary is not None and is_known(secondary):
        hyps[0]["contradicting_evidence_ids"] = list(secondary["evidence_ids"])
        hyps.append(
            {
                "title": str(secondary["value"]),
                "explanation": f"{resolver_name}'s next-ranked candidate, held open because {hyp_field['reason']}",
                "confidence": secondary["confidence"],
                "supporting_evidence_ids": list(secondary["evidence_ids"]),
                "contradicting_evidence_ids": list(primary["evidence_ids"]),
                "assumptions": [
                    f"Assumes {secondary['origin']}'s alternative is at least as representative as the top candidate."
                ],
                "what_would_strengthen": "Founder confirmation, or evidence favoring this label over the top candidate.",
                "what_would_weaken": "Founder confirmation of the top candidate instead.",
            }
        )
    return hyps


def _merge_matching_labels(hyps: list[dict]) -> list[dict]:
    """Two hypotheses from different resolvers naming the exact same label corroborate each other
    — merged into one hypothesis with combined confidence (via `combine_confidence`, not a new
    formula) and unioned evidence, rather than kept as two separate near-duplicate entries."""
    by_label: dict[str, dict] = {}
    order: list[str] = []
    for hyp in hyps:
        key = hyp["title"].strip().lower()
        if key not in by_label:
            by_label[key] = dict(hyp)
            order.append(key)
            continue
        existing = by_label[key]
        merged_evidence_ids = existing["supporting_evidence_ids"] + [
            e for e in hyp["supporting_evidence_ids"] if e not in existing["supporting_evidence_ids"]
        ]
        # Each already-computed confidence is treated as an independent signal for the noisy-OR
        # combination `combine_confidence` already implements — this reuses that exact function
        # rather than defining a second way to combine confidences.
        combined = combine_confidence(
            [
                {"id": "a", "claim": "", "dimension": None, "source_type": "signal_a",
                 "base_confidence": existing["confidence"], "evidence_state": None, "contradicts": []},
                {"id": "b", "claim": "", "dimension": None, "source_type": "signal_b",
                 "base_confidence": hyp["confidence"], "evidence_state": None, "contradicts": []},
            ]
        )
        existing["confidence"] = combined
        existing["supporting_evidence_ids"] = merged_evidence_ids
        existing["explanation"] += f" Corroborated by: {hyp['explanation']}"
    return [by_label[k] for k in order]


def _industry_interpretation(venture_frame: dict) -> list[Hypothesis]:
    industry_signals = _hypothesis_field_signals("The industry classifier", venture_frame["industry"])
    positioning_signals = _hypothesis_field_signals("Venture positioning", venture_frame["positioning"])
    merged = _merge_matching_labels(industry_signals + positioning_signals)
    return _finalize_category("industry_interpretation", merged)


def _readiness(funding_assessment: dict | None, evidence_ledger: list[dict]) -> list[Hypothesis]:
    if not funding_assessment or "overall_score" not in funding_assessment:
        return []
    level = funding_assessment["level"]
    score = funding_assessment["overall_score"]
    confidence = combine_confidence(evidence_ledger) if evidence_ledger else 0.0
    hyp = {
        "title": f"Readiness level: {level}",
        "explanation": f"The funding-readiness rubric scored this venture {score}/100, placing it at the '{level}' level.",
        "confidence": confidence,
        "supporting_evidence_ids": [item["id"] for item in evidence_ledger if item["source_type"] == "user_confirmed"],
        "contradicting_evidence_ids": [],
        "assumptions": ["Assumes the rubric's 8 dimensions remain the right lens as the venture evolves."],
        "what_would_strengthen": "Confirming more of the currently unanswered or 'not sure yet' rubric dimensions.",
        "what_would_weaken": "A previously confirmed dimension turning out to be inaccurate.",
    }
    return _finalize_category("readiness", [hyp])


def _major_opportunity(funding_assessment: dict | None, evidence_ledger: list[dict]) -> list[Hypothesis]:
    if not funding_assessment:
        return []
    strong = [
        b for b in funding_assessment.get("breakdown", [])
        if b.get("state") == "confirmed_positive" and b.get("raw_score") == 2
    ]
    if not strong:
        return []
    best = strong[0]
    evidence_id = f"rubric:{best['dimension']}"
    confidence = next((item["base_confidence"] for item in evidence_ledger if item["id"] == evidence_id), 0.0)
    hyp = {
        "title": f"Strongest confirmed signal: {best['label']}",
        "explanation": f"{best['label']}: {best['scale_description']} — the strongest confirmed-positive rubric evidence available.",
        "confidence": confidence,
        "supporting_evidence_ids": [evidence_id],
        "contradicting_evidence_ids": [],
        "assumptions": ["Assumes this strength continues to hold as the venture is validated further."],
        "what_would_strengthen": "Continuing to document this strength as the venture progresses.",
        "what_would_weaken": "New evidence showing this strength was overstated.",
    }
    return _finalize_category("major_opportunity", [hyp])


def _major_risk(funding_assessment: dict | None, venture_frame: dict, evidence_ledger: list[dict]) -> list[Hypothesis]:
    hyps: list[dict] = []
    regulatory = venture_frame.get("regulatory_context")
    if regulatory and is_known(regulatory):
        hyps.append(
            {
                "title": str(regulatory["value"]),
                "explanation": regulatory["supporting_text"] or str(regulatory["value"]),
                "confidence": regulatory["confidence"],
                "supporting_evidence_ids": list(regulatory["evidence_ids"]),
                "contradicting_evidence_ids": [],
                "assumptions": ["Assumes the description accurately reflects the venture's real-world deployment context."],
                "what_would_strengthen": "Legal/regulatory review confirming the applicable requirements.",
                "what_would_weaken": "Founder clarification that this concern doesn't actually apply here.",
            }
        )
    if funding_assessment:
        negatives = [b for b in funding_assessment.get("breakdown", []) if b.get("state") == "confirmed_negative"]
        if negatives:
            worst = negatives[0]
            evidence_id = f"rubric:{worst['dimension']}"
            confidence = next((item["base_confidence"] for item in evidence_ledger if item["id"] == evidence_id), 0.0)
            hyps.append(
                {
                    "title": f"Confirmed gap: {worst['label']}",
                    "explanation": f"{worst['label']}: {worst['scale_description']} — a founder-confirmed absence of evidence.",
                    "confidence": confidence,
                    "supporting_evidence_ids": [evidence_id],
                    "contradicting_evidence_ids": [],
                    "assumptions": ["Assumes this remains unaddressed at the time this analysis is read."],
                    "what_would_strengthen": "This continuing to be unaddressed in later evidence updates.",
                    "what_would_weaken": "The founder providing new evidence for this dimension.",
                }
            )
    if not hyps:
        return []
    return _finalize_category("major_risk", hyps)


def build_hypothesis_set(
    venture_frame: dict,
    evidence_ledger: list[dict] | None = None,
    funding_assessment: dict | None = None,
) -> dict:
    """Assemble the full Hypothesis Set for one analysis run from the Structured Venture Frame
    (Phase B) and Evidence Ledger (Phase A) only — no raw text is read, no new confidence math is
    introduced, and `venture_frame` is only ever read here, never mutated."""
    evidence_ledger = evidence_ledger or []
    categories: dict[str, list[Hypothesis]] = {}

    industry = _industry_interpretation(venture_frame)
    if industry:
        categories["industry_interpretation"] = industry

    customer = _single_field_category("target_customer", venture_frame["customer"], "Founder-stated buyer/user")
    if customer:
        categories["target_customer"] = customer

    business_model = _single_field_category("business_model", venture_frame["revenue_model"], "Revenue-model rubric evidence")
    if business_model:
        categories["business_model"] = business_model

    core_problem = _single_field_category("core_problem", venture_frame["core_venture_summary"], "Founder's own description")
    if core_problem:
        categories["core_problem"] = core_problem

    differentiation = _single_field_category(
        "differentiation", venture_frame["differentiation"], "Competitive-differentiation rubric evidence"
    )
    if differentiation:
        categories["differentiation"] = differentiation

    readiness = _readiness(funding_assessment, evidence_ledger)
    if readiness:
        categories["readiness"] = readiness

    major_opportunity = _major_opportunity(funding_assessment, evidence_ledger)
    if major_opportunity:
        categories["major_opportunity"] = major_opportunity

    major_risk = _major_risk(funding_assessment, venture_frame, evidence_ledger)
    if major_risk:
        categories["major_risk"] = major_risk

    return {"hypothesis_set_version": HYPOTHESIS_SET_VERSION, "categories": categories}
