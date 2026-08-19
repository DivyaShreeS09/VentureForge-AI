"""Decision Synthesis Engine — VentureForge Intelligence Architecture, Phase I.

MISSION. Every prior phase built one reasoning primitive: Evidence Ledger (what do we actually
know), Venture Frame (one structured understanding), Hypothesis Set (competing interpretations),
Confidence Engine (one shared confidence arithmetic), Contradiction Engine (where the picture is
genuinely still open), Alternative Explanation Engine (what else could explain the same evidence).
This module is the first one that **reasons across** all of them instead of reading just one. It
produces exactly one synthesized `DecisionSynthesis` object per analysis — never several competing
ones — and every field on it traces back to a specific upstream structure, never to raw text and
never to a new model/LLM call.

INPUTS consumed (all already computed elsewhere): Evidence Ledger, Venture Frame, Hypothesis Set,
Contradiction Set, Alternative Explanation Set (Phases A-F, via `app.agents.judge.synthesize`'s
return dict), `funding_assessment`, `industry_prediction`, `success_prediction` (Student 1/2),
`strategic_opportunity` (`app.agents.strategic_opportunity`), `founder_guidance_items` (already
merged/ranked by `app.agents.founder_guidance`/`mentor_synthesis`), and Student 3's `ranked_actions`/
`risk_assessment` (`app.agents.student3`). Nothing here re-parses `startup_description`, calls a
classifier, or calls an LLM.

========================================================================================
THE CENTRAL DESIGN QUESTION THIS MODULE HAD TO ANSWER FIRST: what actually counts as "agreement"?

`mentor_verdict` (mentor_synthesis), `strategic_opportunity.primary_opportunity`, and
`founder_guidance_items` are not three independent witnesses to the venture's readiness — they are
three different **narrations of the same upstream Evidence Ledger / funding_assessment**. Counting
"three modules say this venture looks strong" as three votes would be exactly the fake-corroboration
failure mode `app.agents.evidence_ledger.combine_confidence` was built to prevent for evidence items,
just committed one layer up, across modules instead of across evidence sources. This module never
does that. `decision_confidence` is derived **only** from Evidence Ledger + Hypothesis Set +
Contradiction Set — the three structures that carry real, independently-sourced confidence numbers.
Every other input (`funding_assessment`, `industry_prediction`, `success_prediction`,
`strategic_opportunity`, `founder_guidance_items`, Student 3 outputs) is used for two things only:
(a) selecting *content* (which opportunity, which risk, which action to name), and (b) checking for
genuine *cross-module agreement or disagreement* about that content (e.g. does
`strategic_opportunity.primary_opportunity` name the same domain the Hypothesis Set's leading
positioning hypothesis already named) — never as an additional confidence input to be averaged or
voted with the others.

WEIGHTING RULES (disclosed, all reused from the existing Confidence Engine, no new arithmetic):
  - `decision_confidence` = `confidence_engine.propagate_confidence(overall_evidence_confidence,
    *not_contested_confidences)`, where `not_contested_confidences` is, for every still-open
    `"ambiguity"`/`"true_contradiction"` record in the Contradiction Set, `1 - contradiction.confidence`
    (how confident we are this specific part of the picture is *not* contested). `propagate_confidence`
    is Phase D's own "a conclusion is only as strong as its weakest necessary input" rule — reused
    exactly as designed: a decision genuinely cannot be more confident than its least-settled open
    question allows. `"missing_information"` records are deliberately excluded from this — a routine
    unanswered question is not a conflict, and folding it in here would make every ordinary evidence
    gap look like a contested disagreement, which it is not.
  - Convergence *within* the evidence layer (e.g. two hypothesis categories both independently
    pointing the same direction) is exactly what `combine_confidence`'s noisy-OR already rewards
    inside the Hypothesis Set/Evidence Ledger — this module does not recompute that; it reads the
    resulting confidence values as-is.
  - Cross-module *content* agreement (e.g. Strategic Opportunity's `primary_opportunity` naming the
    same domain the Hypothesis Set's leading positioning hypothesis already named) is recorded as a
    `corroborated_by` note on the relevant field, purely informational — it never changes
    `decision_confidence`, precisely to avoid the double-counting failure mode described above.

CONSISTENCY: every field below is a pure function of the inputs. If any upstream structure changes
(a new evidence item, a resolved contradiction, a different leading hypothesis), every field here —
and both narrative summaries — changes automatically on the next call, because nothing is cached or
computed independently of these inputs.

NO DUPLICATE REASONING: `highest_priority_action` **selects** from `ranked_actions` (Student 3's
existing, dedicated priority-score ranking) or, when unavailable, `founder_guidance_items`' own
priority order — it does not build a third ranking. `highest_priority_risk` applies the exact
regulatory-outranks-rubric-risk precedent `mentor_synthesis`/`strategic_opportunity` already
established (a regulatory `Hypothesis` is identifiable structurally: `app.agents.venture_frame`
never attaches an evidence-ledger id to a regulatory classification, so its `supporting_evidence_ids`
is always `[]` — the same fact used here, not a new rule). `alternative_decisions` is a direct,
unmodified passthrough of the Alternative Explanation Set — Phase F already built exactly this
substrate; recomputing it here would be the duplicate-reasoning failure this phase is required to
avoid.

UNCERTAINTY: when the Hypothesis Set has no `readiness`/`major_opportunity` category at all (a
`funding_assessment` with zero confirmed evidence), `overall_decision` says exactly that — "not
enough evidence yet to reach a decision" — rather than forcing an opinion. `decision_confidence` is
`0.0` in that case, not fabricated.

WHAT THIS PHASE DOES NOT DO (a scope boundary, not an oversight): it does not rewire
`mentor_synthesis`, `strategic_opportunity`, or `student3` to consume this module's output — those
modules run *before* this one in the orchestrator graph (this is necessarily the last reasoning node,
since it is the only one with access to everything). Making every upstream narrator consume this
module's decision instead of computing its own is exactly what a future "Unified Action Planning"
phase would do; attempting it here would mean either reordering the graph (a redesign, out of scope)
or duplicating each of those modules' logic a second time inside this one (forbidden). This module
establishes the single reasoning authority going forward; wiring existing narrators to defer to it is
future work, stated here as a limitation rather than silently skipped.
"""

from __future__ import annotations

from typing import TypedDict

from app.agents.confidence_engine import label_confidence, propagate_confidence

DECISION_SYNTHESIS_VERSION = "v1"

_UNRESOLVED_CONTRADICTION_KINDS = ("ambiguity", "true_contradiction")
_ACTIONABLE_GUIDANCE_CATEGORIES = ("discovery_question", "validation_opportunity")

# The one severity ranking this module uses to compare "worst" across a Contradiction Set record
# and a Student 3 RiskItem (both already use the "low"/"medium"/"high" severity vocabulary
# app.agents.contradiction_engine established) — defined once and reused by both call sites in
# `_highest_priority_risk` below, rather than duplicated inline twice.
_SEVERITY_RANK: dict[str, int] = {"high": 2, "medium": 1, "low": 0}


class DecisionSynthesis(TypedDict):
    decision_synthesis_version: str
    overall_decision: str
    decision_confidence: float
    decision_confidence_label: str
    decision_rationale: str
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    remaining_uncertainties: list[dict]
    highest_priority_opportunity: dict | None
    highest_priority_risk: dict | None
    highest_priority_action: dict | None
    highest_learning_goal: dict | None
    highest_validation_goal: dict | None
    why_this_decision: str
    what_would_change_this_decision: list[str]
    alternative_decisions: list[dict]
    mentor_summary: str
    investor_summary: str
    reasoning_trace: list[dict]


def _leading(hyps: list[dict] | None) -> dict | None:
    if not hyps:
        return None
    return next((h for h in hyps if h["status"] == "leading"), hyps[0])


def _category(hypothesis_set: dict, name: str) -> list[dict]:
    return (hypothesis_set or {}).get("categories", {}).get(name, [])


def _unresolved_contradictions(contradiction_set: dict | None) -> list[dict]:
    return [
        c for c in (contradiction_set or {}).get("contradictions", [])
        if c.get("kind") in _UNRESOLVED_CONTRADICTION_KINDS
    ]


def _missing_information(contradiction_set: dict | None) -> list[dict]:
    return [c for c in (contradiction_set or {}).get("contradictions", []) if c.get("kind") == "missing_information"]


def _decision_confidence(evidence_ledger_summary: dict, unresolved: list[dict]) -> float:
    overall = (evidence_ledger_summary or {}).get("overall_confidence", 0.0)
    not_contested = [round(1.0 - c["confidence"], 4) for c in unresolved]
    return propagate_confidence(overall, *not_contested)


def _regulatory_risk_hypothesis(major_risk_hyps: list[dict]) -> dict | None:
    """A regulatory-classification Hypothesis never carries an evidence-ledger id (see
    `app.agents.venture_frame._regulatory_context_field`) — that structural fact, not a new rule,
    is what distinguishes it from a confirmed-negative rubric-gap Hypothesis in the same category."""
    return next((h for h in major_risk_hyps if h["supporting_evidence_ids"] == []), None)


def _highest_priority_opportunity(hypothesis_set: dict, venture_frame: dict, strategic_opportunity: dict | None) -> dict | None:
    major_opportunity = _leading(_category(hypothesis_set, "major_opportunity"))
    primary_domain = None
    positioning = (venture_frame or {}).get("positioning") or {}
    if positioning.get("primary") and positioning["primary"].get("value") is not None:
        primary_domain = positioning["primary"]["value"]

    strategic_primary = (strategic_opportunity or {}).get("primary_opportunity")
    corroborated = bool(
        strategic_primary and primary_domain and str(strategic_primary.get("opportunity", "")).strip().lower() == str(primary_domain).strip().lower()
    )

    if major_opportunity is not None:
        return {
            "title": major_opportunity["title"],
            "description": major_opportunity["explanation"],
            "confidence": major_opportunity["confidence"],
            "source": "evidence_ledger",
            "supporting_evidence_ids": list(major_opportunity["supporting_evidence_ids"]),
            "corroborated_by": ["strategic_opportunity"] if corroborated else [],
        }
    if strategic_primary is not None:
        return {
            "title": strategic_primary.get("opportunity"),
            "description": strategic_primary.get("reason", ""),
            "confidence": None,
            "source": "strategic_opportunity",
            "supporting_evidence_ids": [],
            "corroborated_by": [],
            "note": (
                "No confirmed-positive rubric evidence yet supports a stronger, evidence-linked "
                "opportunity — this is broader strategic reasoning, not a confirmed strength."
            ),
        }
    return None


def _highest_priority_risk(
    hypothesis_set: dict, unresolved_contradictions: list[dict], risk_assessment: list[dict] | None
) -> dict | None:
    major_risk_hyps = _category(hypothesis_set, "major_risk")
    regulatory = _regulatory_risk_hypothesis(major_risk_hyps)
    if regulatory is not None:
        return {
            "title": regulatory["title"],
            "description": regulatory["explanation"],
            "confidence": regulatory["confidence"],
            "source": "evidence_ledger",
            "supporting_evidence_ids": list(regulatory["supporting_evidence_ids"]),
            "reason_ranked_first": "Regulatory/legal exposure outranks an ordinary rubric gap regardless of confidence — the same precedent app.agents.mentor_synthesis/strategic_opportunity already apply.",
        }
    leading_risk = _leading(major_risk_hyps)
    if leading_risk is not None:
        return {
            "title": leading_risk["title"],
            "description": leading_risk["explanation"],
            "confidence": leading_risk["confidence"],
            "source": "evidence_ledger",
            "supporting_evidence_ids": list(leading_risk["supporting_evidence_ids"]),
            "reason_ranked_first": "The strongest confirmed-negative rubric evidence available.",
        }
    if unresolved_contradictions:
        worst = max(unresolved_contradictions, key=lambda c: _SEVERITY_RANK[c["severity"]])
        return {
            "title": worst["title"],
            "description": worst["description"],
            "confidence": worst["confidence"],
            "source": "contradiction_set",
            "supporting_evidence_ids": list(worst["supporting_evidence_ids"]),
            "reason_ranked_first": "The highest-severity still-open contradiction, in the absence of any confirmed rubric or regulatory risk.",
        }
    if risk_assessment:
        worst = max(risk_assessment, key=lambda r: _SEVERITY_RANK.get(r.get("severity"), 0))
        return {
            "title": worst["title"],
            "description": worst.get("mitigation", ""),
            "confidence": None,
            "source": "student3_risk_assessment",
            "supporting_evidence_ids": [],
            "reason_ranked_first": "No evidence-ledger-linked or regulatory risk exists yet; the highest-severity planning risk from Student 3's fixed risk taxonomy.",
        }
    return None


def _highest_priority_action(ranked_actions: list[dict] | None, founder_guidance_items: list[dict] | None) -> dict | None:
    if ranked_actions:
        top = ranked_actions[0]
        return {
            "title": top["title"],
            "description": top.get("evidence_basis", [None])[0] or "",
            "source": "student3_ranked_actions",
            "priority_score": top.get("priority_score"),
        }
    guidance = sorted(
        (item for item in (founder_guidance_items or []) if item["category"] in _ACTIONABLE_GUIDANCE_CATEGORIES),
        key=lambda i: i["priority"],
    )
    if guidance:
        top = guidance[0]
        return {
            "title": top["next_step"],
            "description": top.get("observation", ""),
            "source": "founder_guidance_items",
            "priority_score": None,
        }
    return None


def _highest_guidance_goal(founder_guidance_items: list[dict] | None, category: str) -> dict | None:
    matches = sorted(
        (item for item in (founder_guidance_items or []) if item["category"] == category),
        key=lambda i: i["priority"],
    )
    if not matches:
        return None
    top = matches[0]
    return {"title": top["title"], "next_step": top["next_step"], "why_it_matters": top["why_it_matters"]}


def _overall_decision(readiness_hyp: dict | None, positioning_hyp: dict | None) -> str:
    if readiness_hyp is None and positioning_hyp is None:
        return "There isn't enough confirmed evidence yet to reach a decision — this isn't a negative verdict, just an honest reflection of what's been submitted so far."
    parts = []
    if positioning_hyp is not None:
        parts.append(f"a venture positioned as {positioning_hyp['title']}")
    if readiness_hyp is not None:
        parts.append(f"currently at the '{readiness_hyp['title'].replace('Readiness level: ', '')}' readiness level")
    return "This is " + " ".join(parts) + "."


def _decision_rationale(readiness_hyp: dict | None, evidence_ledger_summary: dict, unresolved: list[dict]) -> str:
    overall_confidence = (evidence_ledger_summary or {}).get("overall_confidence", 0.0)
    base = f"This reasoning rests on evidence combining to {label_confidence(overall_confidence)} overall confidence ({overall_confidence:.2f})."
    if readiness_hyp is not None:
        base += f" {readiness_hyp['explanation']}"
    if unresolved:
        base += f" {len(unresolved)} part(s) of the picture are still genuinely open and have been weighed into the confidence above, not ignored."
    else:
        base += " No unresolved ambiguity or contradiction currently weighs against this."
    return base


def _why_this_decision(readiness_hyp: dict | None) -> str:
    if readiness_hyp is None or readiness_hyp.get("self_critique") is None:
        return "No single leading hypothesis with enough evidence exists yet to explain a preference one way or another."
    return readiness_hyp["self_critique"]["why_this_might_be_wrong"]


def _what_would_change_this_decision(unresolved: list[dict], alternative_explanations: list[dict]) -> list[str]:
    items = [c["recommended_investigation"] for c in unresolved]
    items += [a["recommended_experiment"] for a in alternative_explanations]
    # Preserve order, drop exact duplicates (e.g. the same investigation surfaced by both
    # detectors) without re-deriving anything new.
    seen: set[str] = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _mentor_summary(overall_decision: str, opportunity: dict | None, risk: dict | None, action: dict | None) -> str:
    sentence = overall_decision
    if opportunity is not None:
        sentence += f" Your strongest lead right now is {opportunity['title']}."
    if risk is not None:
        sentence += f" The thing most worth watching is {risk['title'].lower()}."
    if action is not None:
        sentence += f" Your next concrete step: {action['title'].lower()}."
    return sentence


def _investor_summary(readiness_hyp: dict | None, opportunity: dict | None, risk: dict | None, decision_confidence: float) -> str:
    level = readiness_hyp["title"].replace("Readiness level: ", "") if readiness_hyp else "not yet assessable"
    sentence = f"Readiness: {level}, evidence confidence {label_confidence(decision_confidence)} ({decision_confidence:.2f})."
    if opportunity is not None:
        sentence += f" Primary opportunity: {opportunity['title']}."
    if risk is not None:
        sentence += f" Primary risk: {risk['title']}."
    return sentence


def _reasoning_trace(
    readiness_hyp: dict | None,
    unresolved: list[dict],
    missing: list[dict],
    corroborated_opportunity: bool,
) -> list[dict]:
    return [
        {
            "question": "What do multiple modules independently agree on?",
            "answer": (
                "The Strategic Opportunity module's primary opportunity names the same domain the "
                "Hypothesis Set's leading positioning hypothesis already identified."
                if corroborated_opportunity
                else "No genuine cross-module agreement (beyond restating the same evidence) was found this run."
            ),
        },
        {
            "question": "Which modules disagree?",
            "answer": (
                f"{len(unresolved)} unresolved ambiguity/contradiction record(s) — see conflicting_evidence."
                if unresolved
                else "No unresolved disagreement was found."
            ),
        },
        {
            "question": "Which hypothesis survives every challenge?",
            "answer": (
                f"'{readiness_hyp['title']}' — the leading readiness hypothesis, still ranked leading after every contradiction and alternative check."
                if readiness_hyp is not None
                else "No leading hypothesis exists yet to survive a challenge."
            ),
        },
        {
            "question": "What uncertainty remains?",
            "answer": f"{len(missing)} open question(s) with no evidence yet; {len(unresolved)} genuinely contested point(s).",
        },
    ]


def build_decision_synthesis(
    evidence_ledger: list[dict] | None = None,
    evidence_ledger_summary: dict | None = None,
    venture_frame: dict | None = None,
    hypothesis_set: dict | None = None,
    contradiction_set: dict | None = None,
    alternative_explanation_set: dict | None = None,
    funding_assessment: dict | None = None,
    industry_prediction: dict | None = None,
    success_prediction: dict | None = None,
    strategic_opportunity: dict | None = None,
    founder_guidance_items: list[dict] | None = None,
    ranked_actions: list[dict] | None = None,
    risk_assessment: list[dict] | None = None,
) -> DecisionSynthesis:
    """Assemble the one canonical Decision Synthesis object for an analysis run. Deterministic and
    idempotent: identical inputs always produce an equal output. See module docstring for the full
    audit of what is reused, what is newly reasoned across, and the disclosed weighting rules.
    """
    hypothesis_set = hypothesis_set or {"categories": {}}
    venture_frame = venture_frame or {}
    contradiction_set = contradiction_set or {"contradictions": []}
    alternative_explanation_set = alternative_explanation_set or {"alternative_explanations": []}
    evidence_ledger_summary = evidence_ledger_summary or {}

    readiness_hyp = _leading(_category(hypothesis_set, "readiness"))
    positioning_hyp = _leading(_category(hypothesis_set, "industry_interpretation"))

    unresolved = _unresolved_contradictions(contradiction_set)
    missing = _missing_information(contradiction_set)

    decision_confidence = _decision_confidence(evidence_ledger_summary, unresolved)

    opportunity = _highest_priority_opportunity(hypothesis_set, venture_frame, strategic_opportunity)
    risk = _highest_priority_risk(hypothesis_set, unresolved, risk_assessment)
    action = _highest_priority_action(ranked_actions, founder_guidance_items)
    learning_goal = _highest_guidance_goal(founder_guidance_items, "discovery_question")
    validation_goal = _highest_guidance_goal(founder_guidance_items, "validation_opportunity")

    supporting_evidence: list[str] = []
    for category_hyps in (hypothesis_set.get("categories") or {}).values():
        leading = _leading(category_hyps)
        if leading is not None:
            for evidence_id in leading["supporting_evidence_ids"]:
                if evidence_id not in supporting_evidence:
                    supporting_evidence.append(evidence_id)

    conflicting_evidence: list[str] = []
    for record in unresolved:
        for evidence_id in record["conflicting_evidence_ids"]:
            if evidence_id not in conflicting_evidence:
                conflicting_evidence.append(evidence_id)
    for alt in alternative_explanation_set.get("alternative_explanations", []):
        for evidence_id in alt.get("contradicting_evidence_ids", []):
            if evidence_id not in conflicting_evidence:
                conflicting_evidence.append(evidence_id)

    remaining_uncertainties = [
        {"category": c["category"], "kind": c["kind"], "description": c["description"]}
        for c in unresolved + missing
    ]

    overall_decision = _overall_decision(readiness_hyp, positioning_hyp)
    decision_rationale = _decision_rationale(readiness_hyp, evidence_ledger_summary, unresolved)
    why_this = _why_this_decision(readiness_hyp)
    what_would_change = _what_would_change_this_decision(unresolved, alternative_explanation_set.get("alternative_explanations", []))
    mentor_summary = _mentor_summary(overall_decision, opportunity, risk, action)
    investor_summary = _investor_summary(readiness_hyp, opportunity, risk, decision_confidence)
    corroborated_opportunity = bool(opportunity and opportunity.get("corroborated_by"))
    reasoning_trace = _reasoning_trace(readiness_hyp, unresolved, missing, corroborated_opportunity)

    return {
        "decision_synthesis_version": DECISION_SYNTHESIS_VERSION,
        "overall_decision": overall_decision,
        "decision_confidence": decision_confidence,
        "decision_confidence_label": label_confidence(decision_confidence),
        "decision_rationale": decision_rationale,
        "supporting_evidence": supporting_evidence,
        "conflicting_evidence": conflicting_evidence,
        "remaining_uncertainties": remaining_uncertainties,
        "highest_priority_opportunity": opportunity,
        "highest_priority_risk": risk,
        "highest_priority_action": action,
        "highest_learning_goal": learning_goal,
        "highest_validation_goal": validation_goal,
        "why_this_decision": why_this,
        "what_would_change_this_decision": what_would_change,
        "alternative_decisions": list(alternative_explanation_set.get("alternative_explanations", [])),
        "mentor_summary": mentor_summary,
        "investor_summary": investor_summary,
        "reasoning_trace": reasoning_trace,
    }
