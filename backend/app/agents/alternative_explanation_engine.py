"""Alternative Explanation Engine — VentureForge Intelligence Architecture, Phase F.

FIRST (audit): every module that currently reaches a conclusion, and where a single explanation is
assumed:

  - `app.ml.predictor` (industry) / `app.agents.venture_positioning` (positioning) — each resolves to
    one `predicted_industry`/`primary_domain`. Phase B/C already open this up exactly once (a single
    next-ranked alternative, surfaced only when the resolver itself reports `is_uncertain`/
    `is_low_confidence`) — see `app.agents.hypothesis_set._industry_interpretation`. This is the one
    place in the whole pipeline that already holds more than one candidate open at all.
  - `app.agents.venture_frame` (`target_customer`, `business_model`/`differentiation` via
    `revenue_model_clarity`/`competitive_differentiation`, `core_problem`) — each is built from
    exactly one upstream field (`market_evidence.customer_type`, one rubric dimension, the business
    model agent's extracted value proposition) with no second candidate anywhere in the data model.
    A single explanation is assumed here because, honestly, only one exists to assume from.
  - `app.agents.hypothesis_set` (`readiness`, `major_opportunity`, `major_risk`) — each built from
    exactly one funding-readiness signal (the overall level; the single strongest confirmed
    dimension; the single first regulatory or confirmed-negative dimension found). A single
    explanation is assumed, though for `major_risk` specifically the *interpretation* of a confirmed
    gap (e.g. "no traction") can honestly have an alternative reading given a second, independent
    Frame field (venture stage) — see `_stage_gated_alternatives` below, the one case in this phase
    where a genuine second explanation for the same evidence is available without fabricating one.
  - `app.agents.mentor_synthesis` (mentor verdict, `biggest_risk`), `app.agents.founder_guidance`
    (guidance items), `app.agents.strategic_opportunity`, `app.agents.student3` — all of these are
    *narrators/consumers* of the single-hypothesis conclusions listed above; none of them performs
    its own independent single-explanation reasoning that this phase's data model could open up
    further. Broadening the search space at the `hypothesis_set`/`venture_frame` layer (below) is
    therefore sufficient to reach every one of these consumers once Decision Synthesis (Phase I)
    wires alternative explanations into them — this phase does not touch any of them directly (no
    endpoint/UI/architecture change is in scope).

SECOND — one canonical engine, consuming only Evidence Ledger + Venture Frame + Hypothesis Set +
Contradiction Set (never raw text, never a new industry/taxonomy computation of its own). Two
detectors, each reusing an already-computed signal rather than inventing one:

  1. `_hypothesis_alternatives` — for every Hypothesis Set category the Contradiction Engine has
     already flagged as `"ambiguity"` (Phase E's own signal — reused here as the entry gate so this
     phase's judgment about "is there a genuine open alternative" is never computed twice), every
     non-leading, non-rejected hypothesis in that category becomes a fully-specified
     `AlternativeExplanation`. Every field below is either copied directly from the Hypothesis Set's
     own already-computed data (`confidence`, `supporting_evidence_ids`, `contradicting_evidence_ids`,
     `assumptions`, `what_would_strengthen`/`what_would_weaken`) or reused from the *leading*
     hypothesis's own `self_critique` (`why_this_might_be_wrong` -> `why_primary_may_be_incomplete`;
     `experiment_to_resolve_uncertainty` -> `recommended_experiment`) — both already built by
     `app.agents.hypothesis_set._self_critique`. Nothing here is a new computation; it is a
     restructuring of existing, evidence-linked content into the schema this phase requires.
  2. `_stage_gated_alternatives` — the one place a genuine *second* explanation for the same evidence
     is honestly available: a confirmed-negative `traction` rubric answer and the founder's own
     `venture_stage` (an independent Frame field: `market_evidence.startup_stage`) can both be true at
     once, and an idea/mvp-stage venture with no traction yet is not read the same way as a
     growth-stage venture with no traction. This is the module docstring's own worked example
     ("too early to measure"). The other four example alternatives named in the brief ("wrong
     customer," "weak distribution," "product still evolving," "validation method unsuitable") are
     deliberately NOT implemented — no Evidence Ledger/Venture Frame/Hypothesis Set field
     distinguishes any of them from the others without either parsing raw text or inventing a new,
     undisclosed signal, both forbidden by this phase's rules. Documented as a limitation, not
     silently skipped.

Positioning/industry alternatives beyond the single already-open secondary (e.g. "Healthcare
Software" vs. "Clinical Decision Support" vs. "Medical Workflow Automation" vs. "Provider
Productivity Tool," all ranked candidates already computed by `app.ml.positioning_taxonomy.
score_taxonomy` and passed through `app.agents.judge.synthesize` as `taxonomy_candidates`) are **not**
sourced here, even though the raw data exists upstream: this phase's own mandate restricts input to
Evidence Ledger + Venture Frame + Hypothesis Set + Contradiction Set, and the Venture Frame's
`HypothesisField` (Phase B) only ever carries a primary and a single secondary candidate — reaching
past that into `taxonomy_candidates` directly would violate the stated input boundary, and widening
`HypothesisField` to carry a full ranked list would be a Venture Frame schema change, which is a
larger, riskier change than "additive only" permits this phase. Documented as a limitation: richer
taxonomy-candidate alternatives require a future Venture Frame extension, not a Phase F workaround.

RULES — never fabricate: if a category was not already flagged `"ambiguity"` by the Contradiction
Engine, and it is not the one stage-gated traction case, no alternative is produced for it at all —
see `categories_with_single_explanation` in the returned dict, which says so explicitly rather than
silently omitting the category.
"""

from __future__ import annotations

from typing import TypedDict

from app.agents.confidence_engine import propagate_confidence
from app.agents.contradiction_engine import CATEGORY_INFO
from app.agents.venture_frame import is_known

ALTERNATIVE_EXPLANATION_ENGINE_VERSION = "v1"


class AlternativeExplanation(TypedDict):
    id: str
    category: str
    title: str
    description: str
    confidence: float
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    assumptions: list[str]
    why_primary_may_be_incomplete: str
    distinguishing_evidence: str
    recommended_experiment: str
    expected_outcome_if_true: str
    expected_outcome_if_false: str
    primary_explanation_id: str


def _categories_flagged_ambiguous(contradiction_set: dict | None) -> set[str]:
    """Read (never recompute) which Hypothesis Set categories the Contradiction Engine already
    flagged as genuinely open. Relies on the `"{category}:ambiguity"` id format
    `app.agents.contradiction_engine._ambiguity_contradictions` already establishes."""
    return {
        c["id"].rsplit(":ambiguity", 1)[0]
        for c in (contradiction_set or {}).get("contradictions", [])
        if c.get("kind") == "ambiguity" and c["id"].endswith(":ambiguity")
    }


def _hypothesis_alternatives(hypothesis_set: dict, contradiction_set: dict) -> tuple[list[AlternativeExplanation], set[str]]:
    alternatives: list[AlternativeExplanation] = []
    touched_categories: set[str] = set()
    flagged = _categories_flagged_ambiguous(contradiction_set)
    categories = (hypothesis_set or {}).get("categories", {})
    for category_name in flagged:
        hyps = categories.get(category_name)
        info = CATEGORY_INFO.get(category_name)
        if not hyps or not info:
            continue
        leading = next((h for h in hyps if h["status"] == "leading"), None)
        if leading is None or leading.get("self_critique") is None:
            continue
        for hyp in hyps:
            if hyp["id"] == leading["id"] or hyp["status"] == "rejected":
                continue
            alternatives.append(
                {
                    "id": f"{category_name}:{hyp['id']}:alternative",
                    "category": info["contradiction_category"],
                    "title": hyp["title"],
                    "description": hyp["explanation"],
                    "confidence": hyp["confidence"],
                    "supporting_evidence_ids": list(hyp["supporting_evidence_ids"]),
                    "contradicting_evidence_ids": list(hyp["contradicting_evidence_ids"]),
                    "assumptions": list(hyp["assumptions"]),
                    "why_primary_may_be_incomplete": leading["self_critique"]["why_this_might_be_wrong"],
                    "distinguishing_evidence": (
                        f'If "{leading["what_would_strengthen"]}" turns out true, the current leading '
                        f'explanation ("{leading["title"]}") holds; if instead "{hyp["what_would_strengthen"]}" '
                        f'turns out true, this alternative ("{hyp["title"]}") becomes the stronger fit.'
                    ),
                    "recommended_experiment": leading["self_critique"]["experiment_to_resolve_uncertainty"],
                    "expected_outcome_if_true": hyp["what_would_strengthen"],
                    "expected_outcome_if_false": hyp["what_would_weaken"],
                    "primary_explanation_id": leading["id"],
                }
            )
            touched_categories.add(category_name)
    return alternatives, touched_categories


def _stage_gated_alternatives(venture_frame: dict, hypothesis_set: dict) -> tuple[list[AlternativeExplanation], set[str]]:
    """The one evidence-grounded alternative to a confirmed traction gap available in this pipeline
    today: the venture's own stage. See module docstring for why the other named traction
    alternatives are not implemented."""
    major_risk = (hypothesis_set or {}).get("categories", {}).get("major_risk", [])
    leading = next((h for h in major_risk if h["status"] == "leading"), None)
    if leading is None or "rubric:traction" not in leading["supporting_evidence_ids"]:
        return [], set()
    venture_stage = (venture_frame or {}).get("venture_stage")
    if not venture_stage or not is_known(venture_stage):
        return [], set()
    if venture_stage["value"] not in ("idea", "mvp"):
        return [], set()
    confidence = propagate_confidence(leading["confidence"], venture_stage["confidence"])
    return (
        [
            {
                "id": "major_risk:too_early_to_measure:alternative",
                "category": "evidence_contradiction",
                "title": "Too early to measure",
                "description": (
                    "The rubric shows no confirmed traction yet, but the venture is still at the "
                    f'"{venture_stage["value"]}" stage — at this point, an absence of traction may simply '
                    "reflect timing rather than a real weakness in the venture itself."
                ),
                "confidence": confidence,
                "supporting_evidence_ids": list(venture_stage["evidence_ids"]),
                "contradicting_evidence_ids": [],
                "assumptions": ["Assumes the founder's stated venture stage still accurately reflects where the venture is today."],
                "why_primary_may_be_incomplete": (
                    "A confirmed absence of traction reads the same whether a venture has been trying and "
                    "failing to gain traction, or simply hasn't reached the stage where traction is expected "
                    "yet — the rubric answer alone cannot distinguish the two."
                ),
                "distinguishing_evidence": (
                    "Whether traction evidence appears once the venture reaches a later stage (e.g. "
                    "mvp/early_traction) would distinguish 'too early to measure' from a genuine traction gap."
                ),
                "recommended_experiment": "Revisit this rubric dimension once the venture reaches its next stage milestone.",
                "expected_outcome_if_true": "Traction evidence appears naturally once the venture reaches a later stage.",
                "expected_outcome_if_false": "Traction remains unconfirmed even after the venture advances to a later stage.",
                "primary_explanation_id": leading["id"],
            }
        ],
        {"major_risk"},
    )


def _single_explanation_categories(hypothesis_set: dict, touched_categories: set[str]) -> list[dict]:
    """SELF CHALLENGE, made explicit: for every category not already given an alternative above,
    record that the question was asked and nothing evidence-supported was found — never silently
    omitted."""
    result: list[dict] = []
    for category_name, hyps in (hypothesis_set or {}).get("categories", {}).items():
        if category_name in touched_categories or not hyps:
            continue
        leading = next((h for h in hyps if h["status"] == "leading"), hyps[0])
        result.append(
            {
                "category": category_name,
                "leading_explanation": leading["title"],
                "note": (
                    "No evidence-supported alternative was found — the leading explanation is the only "
                    "one the current evidence honestly supports."
                ),
            }
        )
    return result


def build_alternative_explanation_set(
    evidence_ledger: list[dict] | None = None,
    venture_frame: dict | None = None,
    hypothesis_set: dict | None = None,
    contradiction_set: dict | None = None,
) -> dict:
    """Assemble the full Alternative Explanation Set for one analysis run from the Evidence Ledger,
    Venture Frame, Hypothesis Set, and Contradiction Set only. Deterministic and idempotent:
    identical inputs always produce an equal output. This phase does not make decisions — Decision
    Synthesis (Phase I) is the intended consumer. `evidence_ledger` is accepted per the architecture's
    instruction that everything derive from these four structures, but is not read directly today:
    both detectors below already reason from ledger-derived data one layer up (hypothesis
    confidences, Frame field confidences) — kept as an explicit parameter so a future detector
    needing raw ledger items has it available without changing this function's signature.
    """
    hypothesis_set = hypothesis_set or {"categories": {}}
    venture_frame = venture_frame or {}
    contradiction_set = contradiction_set or {"contradictions": []}

    alternatives: list[AlternativeExplanation] = []
    touched: set[str] = set()

    hyp_alternatives, hyp_touched = _hypothesis_alternatives(hypothesis_set, contradiction_set)
    alternatives.extend(hyp_alternatives)
    touched |= hyp_touched

    stage_alternatives, stage_touched = _stage_gated_alternatives(venture_frame, hypothesis_set)
    alternatives.extend(stage_alternatives)
    touched |= stage_touched

    return {
        "alternative_explanation_engine_version": ALTERNATIVE_EXPLANATION_ENGINE_VERSION,
        "alternative_explanations": alternatives,
        "categories_with_single_explanation": _single_explanation_categories(hypothesis_set, touched),
    }
