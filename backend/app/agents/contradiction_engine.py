"""Global Contradiction Detection — VentureForge Intelligence Architecture, Phase E.

FIRST (audit): every existing contradiction-adjacent check in this repository, found before writing
a line of new logic here:

  - `app.agents.mentor_synthesis._contradiction_note` — compares the founder's own free-form
    `startup_description` text against their structured `customer_type` answer, using substring
    containment so "restaurant"/"restaurants" never trip it. This is a **raw-text** check producing
    one founder-facing sentence folded into `business_context`. Per this phase's own mandate
    ("never from raw text"), this engine does not re-derive or duplicate it — it is a different kind
    of check (text vs. text) serving a different purpose (one narrated sentence, not a structured,
    reasoned record), and stays exactly where it is. **Kept, not merged.**
  - `app.agents.hypothesis_set` — Phase C already produces the one genuine *structural* conflict
    signal available today: a `Hypothesis["contradicting_evidence_ids"]` populated only when a
    resolver's own Phase B output flagged itself `is_ambiguous` (industry classifier vs. its own
    next-ranked alternative, or venture positioning vs. its own next-ranked taxonomy candidate).
    This is the raw material this engine promotes into full `Contradiction` records — not
    duplicated logic, a *consumer* of Phase C's existing, deliberately conservative signal.
  - `app.agents.venture_frame.HypothesisField.is_ambiguous`/`reason` — the same signal one layer
    earlier; `hypothesis_set` already reads it, so this engine reads `hypothesis_set`, not the frame
    directly, to avoid a second path to the same fact.
  - `app.agents.venture_frame._open_questions` / `funding_assessment.missing_evidence` — an existing,
    already-computed list of dimensions with no evidence at all. Read here as the source for
    "missing information" records; not recomputed.
  - `app.agents.mentor_synthesis` roadmap-consistency comment (readiness level vs. roadmap framing)
    and `strategic_opportunity`'s regulatory-risk headline/detail-consistency comment: both describe
    *presentation* consistency the authors already engineered by construction (reusing one shared
    function/flag so two renderings can't diverge) — neither is a "detect a conflict in evidence"
    computation, so there is nothing to migrate here.
  - `app.ml.predictor` / `app.ml.positioning_taxonomy` / `app.agents.venture_positioning` ambiguity
    thresholds (`is_uncertain`, `is_low_confidence`, `AMBIGUITY_MARGIN`) — these *produce* the
    is_ambiguous flags `hypothesis_set` already consumes. **Kept as-is** (they are the origin of the
    signal, not a duplicate consumer of it).

No other module in the repository independently computes a "these two things disagree" judgment.
There is nothing to delete: the only pre-existing structural signal (Phase C's
`contradicting_evidence_ids`) was already a single source, never duplicated, and stays exactly where
it is produced. This module's job is SECOND/THIRD from the brief: give that signal (plus the
Evidence Ledger and Venture Frame's `open_questions`) one shared, richly-explained downstream
representation, and do nothing else independently.

FOURTH/FIFTH — categories and honest scope. `Contradiction["kind"]` is one of four **distinct**
concepts (never collapsed, per the brief's explicit FIFTH requirement):

  - `"ambiguity"` — a single resolver was itself unsure between two candidates (Phase C's
    `is_ambiguous`). Implemented below (`_ambiguity_contradictions`). This is the only kind Phase C's
    existing signal actually represents — see its own docstring, which calls this "ambiguity," not a
    conflict between independent evidence sources. Labeling it "true contradiction" would misrepresent
    what the underlying data actually shows, so it is not.
  - `"missing_information"` — no evidence exists yet for a dimension at all (not a disagreement).
    Implemented below (`_missing_information_items`), read directly from `venture_frame.open_questions`
    (already computed by Phase B; not recomputed here).
  - `"true_contradiction"` — two **independent** evidence sources make claims about the same fact
    that genuinely disagree (not merely differ in specificity — see the SIXTH false-positive note
    below). The `Contradiction` schema fully supports this kind, and `build_contradiction_set` would
    emit it the moment a genuine source for it exists. **Honestly, no such source exists yet in this
    pipeline.** The one place two independent sources could name different things for the same
    concept — the industry classifier vs. venture positioning, both un-ambiguous but naming different
    domains — is *deliberately not* treated as a contradiction: `hypothesis_set`'s own docstring
    explains a classifier's coarse label ("healthcare") and the taxonomy's fine-grained label
    ("Clinical Decision Support") differ in *resolution*, not truth, and the brief's own SIXTH example
    ("Healthcare + Clinical Decision Support should normally strengthen each other") requires exactly
    this restraint. Treating every un-merged pair of differing labels as a "true contradiction" would
    manufacture false positives on the majority of ordinary, non-conflicting ventures — the opposite
    of this phase's mandate. Genuine true-contradiction detection needs a second, *independent*
    evidence source that can conflict with the founder's own account (e.g. a retrieved comparable
    company, Phase M; a prior analysis of the same venture, Phase K) — neither exists yet. Documented
    as a limitation, not silently skipped.
  - `"evolution"` — the venture's own answers changed between two points in time. This requires a
    history of a *previous* analysis of the same venture, which does not exist until Founder Memory
    (Phase K) is built. The schema supports it; nothing in this pipeline can populate it honestly yet.

SIXTH — false-positive protections, explained:
  - Plural/singular and substring variants ("restaurant" vs. "restaurants") never reach this module
    as a source of disagreement in the first place, because this engine never re-parses free text —
    it only reads structured `Hypothesis`/`FrameField` values, and `hypothesis_set._merge_matching_labels`
    already folds matching labels (case/whitespace-normalized) into one hypothesis before this module
    ever sees them.
  - Differences in specificity (coarse industry label vs. fine-grained taxonomy label) are never
    treated as competing claims — see `hypothesis_set._industry_interpretation`'s docstring; this
    engine consumes its output as-is and does not re-derive or second-guess that judgment.
  - A hypothesis category is only promoted to an `"ambiguity"` record when Phase C itself already
    populated `contradicting_evidence_ids` — this module never invents a new similarity/conflict
    check of its own.

SEVENTH — every `Contradiction` answers, in its own fields: `description` explains why it's worth
noticing (in mentor language, never "your inputs conflict"), `supporting_evidence_ids`/
`conflicting_evidence_ids` show what backs each side, `recommended_investigation` says what would
resolve it, and `severity` (a fixed, disclosed per-category judgment — see `CATEGORY_INFO`, the
same "documented constant" idiom `app.agents.founder_guidance._CATEGORY_URGENCY` already uses in
this codebase) gives a signal for whether it is worth acting on now.

EIGHTH — purely additive. This module is read-only over its three inputs (Evidence Ledger, Venture
Frame, Hypothesis Set) and produces one new dict; it does not change, replace, or remove anything
`app.agents.judge.synthesize` already returns. No existing mentor output is altered.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from app.agents.confidence_engine import combine_confidence

CONTRADICTION_ENGINE_VERSION = "v1"

ContradictionKind = Literal["true_contradiction", "ambiguity", "missing_information", "evolution"]
Severity = Literal["low", "medium", "high"]


class Contradiction(TypedDict):
    id: str
    category: str
    kind: ContradictionKind
    title: str
    description: str
    severity: Severity
    confidence: float
    supporting_evidence_ids: list[str]
    conflicting_evidence_ids: list[str]
    affected_modules: list[str]
    recommended_investigation: str
    possible_explanations: list[str]


class CategoryInfo(TypedDict):
    contradiction_category: str
    affected_modules: list[str]
    severity: Severity


# Fixed, disclosed per-category severity and provenance. A judgment call (not learned, no outcome
# data exists to learn it from), analogous in spirit to `app.agents.founder_guidance._CATEGORY_URGENCY`
# — a mapping from category to a fixed priority the same way that module maps dimension to urgency.
# Rationale: a customer or core-problem ambiguity is rated "high" because it determines *who* and
# *what* every downstream recommendation is written for; industry/business-model/readiness ambiguity
# is rated "medium" because later reasoning can often still proceed sensibly with either candidate
# held open; an opportunity-side ambiguity is rated "low" because it affects what to highlight, not
# what to build.
CATEGORY_INFO: dict[str, CategoryInfo] = {
    "industry_interpretation": {
        "contradiction_category": "industry_contradiction",
        "affected_modules": ["app.ml.predictor", "app.agents.venture_positioning"],
        "severity": "medium",
    },
    "target_customer": {
        "contradiction_category": "customer_contradiction",
        "affected_modules": ["market_evidence.customer_type"],
        "severity": "high",
    },
    "business_model": {
        "contradiction_category": "business_model_contradiction",
        "affected_modules": ["app.ml.funding_readiness"],
        "severity": "medium",
    },
    "core_problem": {
        "contradiction_category": "problem_contradiction",
        "affected_modules": ["app.agents.business_model_agent"],
        "severity": "high",
    },
    "differentiation": {
        # Differentiation is the venture's competitive-positioning claim within its business model —
        # no dedicated "differentiation_contradiction" category exists in the brief's example list,
        # and inventing a 13th label for one rubric dimension would add a distinction the founder
        # gains nothing from; it is the same underlying concern as business_model_contradiction.
        "contradiction_category": "business_model_contradiction",
        "affected_modules": ["app.ml.funding_readiness"],
        "severity": "medium",
    },
    "readiness": {
        "contradiction_category": "readiness_contradiction",
        "affected_modules": ["app.ml.funding_readiness"],
        "severity": "medium",
    },
    "major_opportunity": {
        # An opportunity claim rests directly on rubric/regulatory evidence; if it is ever
        # contradicted, the disagreement is about the evidence itself, not a distinct "opportunity"
        # concept — see app.agents.hypothesis_set._major_opportunity.
        "contradiction_category": "evidence_contradiction",
        "affected_modules": ["app.ml.funding_readiness"],
        "severity": "low",
    },
    "major_risk": {
        "contradiction_category": "evidence_contradiction",
        "affected_modules": ["app.ml.funding_readiness", "app.agents.regulatory_context"],
        "severity": "medium",
    },
}

# Named categories from the brief with no dedicated hypothesis_set category to promote from today,
# and why: "Revenue" and "Traction" are individual funding-readiness rubric *dimensions*, already
# folded into the single-hypothesis "business_model" and "major_risk"/"major_opportunity" categories
# above rather than modeled as their own hypothesis categories — a dimension-level contradiction
# would require two competing values for one dimension, which app.ml.funding_readiness structurally
# cannot produce (one state per dimension per run). "Market" and "Technology" have no dedicated
# Venture Frame field or hypothesis category yet (see venture_frame.py's own docstring on fields
# deliberately not stubbed out). "Regulatory" is represented as one of major_risk's two possible
# hypotheses, not a category with its own competing candidates. "Confidence contradiction" (the
# Evidence Ledger's combined confidence disagreeing with a specific hypothesis's own confidence) was
# considered and rejected: `evidence_ledger_summary["overall_confidence"]` is a noisy-OR over *every*
# item in the ledger and is high for nearly any venture with at least one confirmed rubric answer,
# regardless of any single hypothesis's own confidence — flagging every case where the two differ
# would fire on most ventures and would not be a real disagreement, only two different-scoped
# numbers. Not implemented, to honor "false positives must be minimized."


def _combine_pair(a: float, b: float) -> float:
    """Combine two already-computed confidence values as independent signals, using the exact same
    noisy-OR pattern `app.agents.hypothesis_set._merge_matching_labels` already established for
    combining two hypothesis confidences — reused here via the shared `combine_confidence`, not a
    new formula."""
    return combine_confidence(
        [
            {"id": "a", "claim": "", "dimension": None, "source_type": "signal_a", "base_confidence": a, "evidence_state": None, "contradicts": []},
            {"id": "b", "claim": "", "dimension": None, "source_type": "signal_b", "base_confidence": b, "evidence_state": None, "contradicts": []},
        ]
    )


def _ambiguity_contradictions(hypothesis_set: dict) -> list[Contradiction]:
    """Promote Phase C's existing `contradicting_evidence_ids` signal into full `Contradiction`
    records. Reads `hypothesis_set` only — never raw text, never a new evidence-matching heuristic.
    """
    contradictions: list[Contradiction] = []
    categories = (hypothesis_set or {}).get("categories", {})
    for category_name, hyps in categories.items():
        info = CATEGORY_INFO.get(category_name)
        if not info or not hyps:
            continue
        conflicted = [h for h in hyps if h.get("contradicting_evidence_ids")]
        if not conflicted:
            continue
        leading = next((h for h in hyps if h["status"] == "leading"), hyps[0])
        alternative = next((h for h in conflicted if h["id"] != leading["id"]), None)
        if alternative is None:
            continue
        confidence = _combine_pair(leading["confidence"], alternative["confidence"])
        contradictions.append(
            {
                "id": f"{category_name}:ambiguity",
                "category": info["contradiction_category"],
                "kind": "ambiguity",
                "title": f"Two readings of {category_name.replace('_', ' ')} are still open",
                "description": (
                    f'"{leading["title"]}" is the leading interpretation, but "{alternative["title"]}" '
                    "hasn't been ruled out yet. This isn't two pieces of evidence pulling in different "
                    "directions — the underlying signal itself flagged this as uncertain, and clarifying "
                    "it will improve the recommendations."
                ),
                "severity": info["severity"],
                "confidence": confidence,
                "supporting_evidence_ids": list(leading["supporting_evidence_ids"]),
                "conflicting_evidence_ids": list(alternative["supporting_evidence_ids"]),
                "affected_modules": list(info["affected_modules"]),
                "recommended_investigation": (
                    f'Confirm directly with the founder which better describes the venture: '
                    f'"{leading["title"]}" or "{alternative["title"]}".'
                ),
                "possible_explanations": [
                    "The underlying classifier/resolver was not confident enough to commit to a single answer.",
                    "The founder's description may genuinely support either reading equally well today.",
                    "One additional confirming detail from the founder would likely resolve this.",
                ],
            }
        )
    return contradictions


def _missing_information_items(venture_frame: dict) -> list[Contradiction]:
    """One record per open question already computed by `app.agents.venture_frame` — read, not
    recomputed. Confidence is 1.0 here because there is no uncertainty about the fact itself (the
    absence of evidence is directly observed, not inferred); severity is fixed low because a gap is
    routine at this stage, not a warning sign — see `app.agents.founder_guidance` for the existing,
    unduplicated logic that already turns the same gaps into founder-facing discovery questions."""
    open_questions = (venture_frame or {}).get("open_questions") or []
    items: list[Contradiction] = []
    for label in open_questions:
        slug = label.strip().lower().replace(" ", "_").replace("/", "_")
        items.append(
            {
                "id": f"missing_information:{slug}",
                "category": "missing_information",
                "kind": "missing_information",
                "title": f"{label} is still an open question",
                "description": (
                    f"There isn't yet any founder-confirmed evidence for {label.lower()}. This isn't a "
                    "contradiction — it's simply a gap the current evidence doesn't cover yet."
                ),
                "severity": "low",
                "confidence": 1.0,
                "supporting_evidence_ids": [],
                "conflicting_evidence_ids": [],
                "affected_modules": ["app.ml.funding_readiness"],
                "recommended_investigation": f"Ask the founder directly about {label.lower()}.",
                "possible_explanations": [
                    "The founder hasn't been asked this question yet.",
                    "The founder may not have this information themselves yet — that's normal at this stage.",
                ],
            }
        )
    return items


def _counts(contradictions: list[Contradiction]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in contradictions:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    return counts


def build_contradiction_set(
    evidence_ledger: list[dict] | None = None,
    venture_frame: dict | None = None,
    hypothesis_set: dict | None = None,
) -> dict:
    """Assemble the full Contradiction Set for one analysis run from the Evidence Ledger, Venture
    Frame, and Hypothesis Set only — never from raw text, and never introducing a second confidence
    or ambiguity computation of its own. Deterministic and idempotent: identical inputs always
    produce an equal output. `evidence_ledger` is accepted (per the architecture's own instruction
    that everything derive from Evidence Ledger + Venture Frame + Hypothesis Set) but not read
    directly today — both existing detectors below already reason from ledger-derived data one layer
    up (`hypothesis_set`'s confidences, `venture_frame`'s open_questions); it is kept as an explicit
    parameter so a future detector needing raw ledger items has it available without changing this
    function's signature.
    """
    venture_frame = venture_frame or {}
    hypothesis_set = hypothesis_set or {"categories": {}}

    contradictions: list[Contradiction] = []
    contradictions.extend(_ambiguity_contradictions(hypothesis_set))
    contradictions.extend(_missing_information_items(venture_frame))

    return {
        "contradiction_engine_version": CONTRADICTION_ENGINE_VERSION,
        "contradictions": contradictions,
        "counts_by_kind": _counts(contradictions),
    }
