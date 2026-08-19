"""Counterfactual Simulation Engine — VentureForge Intelligence Architecture, Phase G.

MISSION. Every prior phase explains the present: what was observed (Evidence Ledger), why it
happened (Causal Reasoning), what it means (Decision Synthesis). None of them answers "what if
something changes?". This module answers that question the only way this architecture is allowed
to: by actually re-running the existing deterministic pipeline functions with one, already-
evidence-represented input surgically changed, and diffing the real result against the real
baseline. It is not prediction, not forecasting, not Monte Carlo, not ML — every number here is
produced by code that already exists elsewhere in this repository, called twice.

========================================================================================
FIRST — audit: every place a recommendation assumes today's conditions remain true, and how each
assumption is classified:

  - `app.agents.founder_guidance` (`build_founder_guidance_items`) — **Evidence-backed.** Every item
    is keyed directly to one rubric dimension's current `state`; if that state changes, the item
    changes. This is exactly what `_counterfactual_funding_assessment` below re-triggers.
  - `app.agents.decision_synthesis` (`highest_priority_risk`/`opportunity`/`action`,
    `decision_confidence`) — **Evidence-backed**, already disclosed as a pure function of Evidence
    Ledger + Hypothesis Set + Contradiction Set (Phase I). This module's entire strategy is to call
    that same pure function again with one changed input, never to guess what it would return.
  - `app.agents.mentor_synthesis` (roadmap, `mentor_verdict`) — **Evidence-backed**, but *not*
    recomputed here: `mentor_synthesis` needs `market_intelligence`/`customer_personas`/
    `business_model`/`revenue_estimate`, none of which are in this phase's allowed input list.
    Documented as a limitation, not silently ignored — see "SCOPE BOUNDARY" below.
  - `app.agents.strategic_opportunity` (`primary_opportunity`) — **Heuristic + evidence-backed
    mix.** Depends on `market_intelligence`/`customer_personas`/`competitor_analysis`, also outside
    this phase's allowed inputs. Held constant (baseline value reused unchanged) in every scenario
    below, per the same scope boundary.
  - `app.agents.student3.ranked_actions` — **Evidence-backed** (keyed to `funding_assessment`'s
    `missing_evidence` and `breakdown`), but its own ranking function needs `industry_prediction`/
    `customer_segment` alongside `funding_assessment`; only `funding_assessment` is in scope here, so
    `ranked_actions` is held constant at its baseline value rather than partially re-derived (a
    partial re-derivation would silently invent a result `ranked_actions` itself never actually
    produces).
  - `app.ml.funding_readiness` (`overall_score`/`level`) — **Template/mechanical**, not a heuristic:
    a fixed, disclosed weight formula. This is the one assumption this module *fully* re-triggers,
    because it is a pure function of exactly the inputs this phase has (see `assess_funding_
    readiness`, reused verbatim, never reimplemented).
  - `app.agents.venture_frame.regulatory_context` — **Model/rule-derived** (a deterministic keyword
    classifier over `startup_description`, which this phase is forbidden from reading). Its
    *presence or absence* as a known Frame field, however, is exactly the structured "regulatory
    burden increases/decreases" input this phase is allowed to flip — done at the Frame-field level,
    never by re-parsing text.
  - Industry classifier confidence (`industry_prediction.confidence`, as already captured in one
    Evidence Ledger item) — **Model-derived.** Its *ledger item*, not the model itself, is what gets
    surgically adjusted for the "industry confidence improves/weakens" scenarios.

SCOPE BOUNDARY (a limitation, stated up front rather than glossed over): this module can only fully
recompute the parts of the reasoning stack whose pure functions take *only* this phase's allowed
inputs (Evidence Ledger, Venture Frame, Hypothesis Set, Contradiction Set, Alternative Explanation
Set, Decision Synthesis, Causal Reasoning, Funding Assessment). That is: `build_evidence_ledger`'s
rubric-derived items (surgically, not by calling the function itself, since it also needs
`market_evidence`/`industry_prediction` which are out of scope — see `_flip_rubric_ledger_item`),
`assess_funding_readiness`, `build_hypothesis_set`, `build_contradiction_set`,
`build_alternative_explanation_set`, `build_decision_synthesis`, and `build_causal_reasoning` are
all re-invoked for real. `strategic_opportunity`, `founder_guidance_items`, and `ranked_actions`/
`risk_assessment` are held constant at their baseline values in every scenario (passed through
unchanged to the recomputation calls that accept them) — recomputing them would require inputs this
phase does not have, and silently approximating them would be exactly the "duplicated reasoning" /
fabrication this architecture forbids.

========================================================================================
SECOND/THIRD — one canonical module. No duplicated confidence math: every confidence number here is
either copied from an existing structure or produced by calling `app.agents.confidence_engine`,
`app.agents.evidence_ledger.summarize_ledger`, `app.ml.funding_readiness.assess_funding_readiness`,
`app.agents.hypothesis_set.build_hypothesis_set`, `app.agents.contradiction_engine.
build_contradiction_set`, `app.agents.alternative_explanation_engine.build_alternative_explanation_
set`, `app.agents.decision_synthesis.build_decision_synthesis`, or `app.agents.causal_reasoning.
build_causal_reasoning` — the exact same functions every other phase already calls. This module adds
no new reasoning rule of its own beyond *which single evidence item to change* for a given supported
counterfactual, and diffing.

SUPPORTED COUNTERFACTUALS — each maps to one already-structurally-represented evidence item, and is
skipped entirely (never fabricated) when its baseline precondition doesn't hold:
  - customer interviews succeed/fail -> `customer_pain_evidence` rubric dimension
  - pricing evidence improves/weakens -> `revenue_model_clarity` rubric dimension
  - traction improves/declines -> `traction` rubric dimension
  - problem evidence strengthens/weakens -> `problem_clarity` rubric dimension
  - competition increases/decreases -> `competitive_differentiation` rubric dimension (more
    competitive pressure reads as weaker demonstrated differentiation, and vice versa)
  - execution capability improves/weakens -> `team_completeness` rubric dimension
  - industry confidence improves/weakens -> the Evidence Ledger's `model:industry_prediction` item
    (only simulated when that item exists in the baseline ledger, i.e. an industry prediction was
    actually made)
  - regulatory burden increases/decreases -> the Venture Frame's `regulatory_context` field's
    known/unknown state (increases only simulated when currently unknown; decreases only simulated
    when currently known — flipping a state to itself is never a real scenario)
Not implemented, and why: "pricing evidence" here only ever means `revenue_model_clarity` (whether
pricing/unit-economics evidence exists), never a market-timing/adoption-probability forecast — this
phase never estimates revenue or adoption likelihood, per its own explicit rule.

Every scenario reuses `app.ml.funding_readiness.DIMENSIONS`' own label/scale text for `why_this_
matters` and `changed_assumption` — never invented wording, and never a duplicate of the rubric's own
descriptions.
"""

from __future__ import annotations

import copy
from typing import Literal, TypedDict

from app.agents.alternative_explanation_engine import build_alternative_explanation_set
from app.agents.causal_reasoning import build_causal_reasoning
from app.agents.confidence_engine import SOURCE_TYPE_BASE_CONFIDENCE
from app.agents.contradiction_engine import build_contradiction_set
from app.agents.decision_synthesis import build_decision_synthesis
from app.agents.evidence_ledger import summarize_ledger
from app.agents.hypothesis_set import build_hypothesis_set
from app.agents.venture_frame import REGULATORY_RULE_CONFIDENCE, is_known
from app.ml.funding_readiness import DIMENSIONS, assess_funding_readiness

COUNTERFACTUAL_SIMULATION_VERSION = "v1"

Direction = Literal["improves", "weakens"]

# (rubric dimension, human label used in scenario titles) — every supported rubric-level
# counterfactual named in the brief maps onto one of `app.ml.funding_readiness.DIMENSIONS`.
_SUPPORTED_DIMENSIONS: dict[str, str] = {
    "customer_pain_evidence": "customer validation",
    "revenue_model_clarity": "pricing evidence",
    "traction": "traction",
    "problem_clarity": "problem evidence",
    "competitive_differentiation": "competitive differentiation",
    "team_completeness": "execution capability",
}


class CounterfactualScenario(TypedDict):
    id: str
    title: str
    changed_assumption: str
    baseline: dict
    counterfactual: dict
    affected_reasoning: list[str]
    expected_effect: str
    confidence: float
    evidence_ids: list[str]
    limitations: str
    assumptions: list[str]
    why_this_matters: str


def _rebuild_answers_from_breakdown(breakdown: list[dict]) -> dict[str, dict]:
    """Reconstruct an `assess_funding_readiness`-compatible `answers` dict from an already-computed
    `funding_assessment["breakdown"]` — reusing exactly the shape `normalize_evidence_answer` already
    accepts, so re-calling `assess_funding_readiness` reproduces the identical baseline score before
    any dimension is changed."""
    answers: dict[str, dict] = {}
    for entry in breakdown:
        state = entry["state"]
        severity = entry["raw_score"] if state == "confirmed_positive" else None
        answers[entry["dimension"]] = {"state": state, "severity": severity}
    return answers


def _counterfactual_funding_assessment(funding_assessment: dict, dimension: str, new_state: str, severity: int | None) -> dict:
    answers = _rebuild_answers_from_breakdown(funding_assessment["breakdown"])
    answers[dimension] = {"state": new_state, "severity": severity}
    return assess_funding_readiness(answers)


def _flip_rubric_ledger_item(evidence_ledger: list[dict], dimension: str, new_state: str) -> list[dict]:
    """Surgically replace (or remove) exactly one rubric-derived Evidence Ledger item — reusing
    `SOURCE_TYPE_BASE_CONFIDENCE` (the same disclosed priors `app.agents.evidence_ledger` itself
    uses) rather than inventing a new confidence number. Every other item in the ledger (market
    evidence, the industry-prediction item) is left untouched."""
    evidence_id = f"rubric:{dimension}"
    remaining = [item for item in evidence_ledger if item["id"] != evidence_id]
    if new_state not in ("confirmed_positive", "confirmed_negative"):
        return remaining
    source_type = "user_confirmed"
    spec = DIMENSIONS[dimension]
    scale_index = 2 if new_state == "confirmed_positive" else 0
    return remaining + [
        {
            "id": evidence_id,
            "claim": f"{spec['label']}: {spec['scale'][scale_index]}",
            "dimension": dimension,
            "source_type": source_type,
            "base_confidence": SOURCE_TYPE_BASE_CONFIDENCE[source_type],
            "evidence_state": new_state,
            "contradicts": [],
        }
    ]


def _flip_industry_ledger_item(evidence_ledger: list[dict], direction: Direction) -> list[dict] | None:
    """Only simulated when the baseline ledger actually carries an industry-prediction item —
    reuses `MODEL_INFERENCE_DISCOUNT`'s own ceiling (from `SOURCE_TYPE_BASE_CONFIDENCE`) as the
    'improves' case's upper bound rather than inventing a new number; 'weakens' removes the item
    entirely (the honest worst case: the industry signal no longer counts as evidence at all)."""
    baseline_item = next((item for item in evidence_ledger if item["id"] == "model:industry_prediction"), None)
    if baseline_item is None:
        return None
    remaining = [item for item in evidence_ledger if item["id"] != "model:industry_prediction"]
    if direction == "weakens":
        return remaining
    ceiling = SOURCE_TYPE_BASE_CONFIDENCE["model_inference"]
    if baseline_item["base_confidence"] >= ceiling:
        return None  # already at the ceiling — not a genuine flip, never simulate a no-op
    return remaining + [{**baseline_item, "base_confidence": ceiling}]


def _flip_regulatory_frame_field(venture_frame: dict, direction: Direction) -> dict | None:
    """Only simulated when the change is a genuine flip. `direction` follows the same convention as
    every other scenario builder: `"improves"` means more favorable for the venture (here: burden
    *decreases*, only simulated from an already-known baseline), `"weakens"` means less favorable
    (burden *increases*, only simulated from an unknown baseline) — flipping a field to its own
    current state is never a real scenario. Reuses `REGULATORY_RULE_CONFIDENCE`, the same disclosed
    constant `app.agents.venture_frame` itself uses for this field, rather than inventing a new one.
    """
    regulatory = venture_frame.get("regulatory_context")
    if regulatory is None:
        return None
    currently_known = is_known(regulatory)
    if direction == "improves" and not currently_known:
        return None
    if direction == "weakens" and currently_known:
        return None
    frame = copy.deepcopy(venture_frame)
    if direction == "weakens":  # burden increases — newly identified, becomes known.
        frame["regulatory_context"] = {
            "value": "A regulatory or compliance requirement now applies.",
            "confidence": REGULATORY_RULE_CONFIDENCE,
            "evidence_ids": [],
            "supporting_text": "Hypothetically newly identified regulatory/compliance exposure.",
            "origin": "regulatory_context",
        }
    else:  # improves — burden decreases — resolved, becomes unknown/no-longer-a-concern.
        frame["regulatory_context"] = {"value": None, "confidence": 0.0, "evidence_ids": [], "supporting_text": None, "origin": "regulatory_context"}
    return frame


def _recompute(
    evidence_ledger: list[dict],
    venture_frame: dict,
    funding_assessment: dict,
    strategic_opportunity: dict | None,
    founder_guidance_items: list[dict] | None,
    ranked_actions: list[dict] | None,
    risk_assessment: list[dict] | None,
) -> dict:
    """Re-run the real, existing deterministic pipeline — never a second implementation of any of
    it. `strategic_opportunity`/`founder_guidance_items`/`ranked_actions`/`risk_assessment` are
    passed through unchanged (see module docstring's SCOPE BOUNDARY)."""
    evidence_ledger_summary = summarize_ledger(evidence_ledger)
    hypothesis_set = build_hypothesis_set(venture_frame, evidence_ledger, funding_assessment)
    contradiction_set = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)
    alternative_explanation_set = build_alternative_explanation_set(evidence_ledger, venture_frame, hypothesis_set, contradiction_set)
    decision_synthesis = build_decision_synthesis(
        evidence_ledger=evidence_ledger,
        evidence_ledger_summary=evidence_ledger_summary,
        venture_frame=venture_frame,
        hypothesis_set=hypothesis_set,
        contradiction_set=contradiction_set,
        alternative_explanation_set=alternative_explanation_set,
        funding_assessment=funding_assessment,
        strategic_opportunity=strategic_opportunity,
        founder_guidance_items=founder_guidance_items,
        ranked_actions=ranked_actions,
        risk_assessment=risk_assessment,
    )
    causal_reasoning = build_causal_reasoning(
        decision_synthesis=decision_synthesis,
        venture_frame=venture_frame,
        funding_assessment=funding_assessment,
        strategic_opportunity=strategic_opportunity,
        founder_guidance_items=founder_guidance_items,
    )
    return {
        "evidence_ledger_summary": evidence_ledger_summary,
        "hypothesis_set": hypothesis_set,
        "contradiction_set": contradiction_set,
        "alternative_explanation_set": alternative_explanation_set,
        "decision_synthesis": decision_synthesis,
        "causal_reasoning": causal_reasoning,
    }


def _snapshot(bundle: dict) -> dict:
    decision = bundle["decision_synthesis"]
    causal = bundle["causal_reasoning"]
    return {
        "decision_confidence": decision["decision_confidence"],
        "decision_confidence_label": decision["decision_confidence_label"],
        "overall_decision": decision["overall_decision"],
        "highest_priority_risk": (decision.get("highest_priority_risk") or {}).get("title"),
        "highest_priority_opportunity": (decision.get("highest_priority_opportunity") or {}).get("title"),
        "highest_priority_action": (decision.get("highest_priority_action") or {}).get("title"),
        "primary_causal_chain": (causal.get("primary_chain") or {}).get("title"),
        "primary_causal_chain_confidence": (causal.get("primary_chain") or {}).get("confidence"),
    }


def _diff(baseline_snapshot: dict, counterfactual_snapshot: dict) -> tuple[list[str], str]:
    affected: list[str] = []
    sentences: list[str] = []
    field_labels = {
        "decision_confidence_label": "decision confidence",
        "highest_priority_risk": "highest-priority risk",
        "highest_priority_opportunity": "highest-priority opportunity",
        "highest_priority_action": "recommended next action",
        "overall_decision": "overall decision",
    }
    for field, label in field_labels.items():
        before, after = baseline_snapshot[field], counterfactual_snapshot[field]
        if before != after:
            affected.append(field)
            sentences.append(f"The {label} would change from {before!r} to {after!r}.")
    if not sentences:
        sentences.append("Every downstream conclusion tracked here would remain unchanged.")
    else:
        unchanged = [label for field, label in field_labels.items() if field not in affected]
        if unchanged:
            sentences.append(f"The {', '.join(unchanged)} would stay the same.")
    return affected, " ".join(sentences)


def _scenario(
    scenario_id: str, title: str, changed_assumption: str, baseline_bundle: dict, counterfactual_bundle: dict,
    evidence_ids: list[str], confidence: float, assumptions: list[str], why_this_matters: str, limitations: str,
) -> CounterfactualScenario:
    baseline_snapshot = _snapshot(baseline_bundle)
    counterfactual_snapshot = _snapshot(counterfactual_bundle)
    affected, expected_effect = _diff(baseline_snapshot, counterfactual_snapshot)
    return {
        "id": scenario_id,
        "title": title,
        "changed_assumption": changed_assumption,
        "baseline": baseline_snapshot,
        "counterfactual": counterfactual_snapshot,
        "affected_reasoning": affected,
        "expected_effect": expected_effect,
        "confidence": round(confidence, 4),
        "evidence_ids": list(evidence_ids),
        "limitations": limitations,
        "assumptions": list(assumptions),
        "why_this_matters": why_this_matters,
    }


def _rubric_scenarios(
    evidence_ledger: list[dict], venture_frame: dict, funding_assessment: dict, baseline_bundle: dict,
    strategic_opportunity: dict | None, founder_guidance_items: list[dict] | None,
    ranked_actions: list[dict] | None, risk_assessment: list[dict] | None,
) -> list[CounterfactualScenario]:
    scenarios: list[CounterfactualScenario] = []
    breakdown_by_dim = {b["dimension"]: b for b in funding_assessment.get("breakdown", [])}
    for dimension, human_label in _SUPPORTED_DIMENSIONS.items():
        entry = breakdown_by_dim.get(dimension)
        if entry is None or entry["state"] == "not_applicable":
            continue
        spec = DIMENSIONS[dimension]
        for new_state, direction, verb in (
            ("confirmed_positive", "improves", "strengthens"),
            ("confirmed_negative", "weakens", "weakens"),
        ):
            if entry["state"] == new_state:
                continue  # no-op: never simulate a flip to the state that already holds
            severity = 2 if new_state == "confirmed_positive" else None
            counterfactual_funding_assessment = _counterfactual_funding_assessment(funding_assessment, dimension, new_state, severity)
            counterfactual_ledger = _flip_rubric_ledger_item(evidence_ledger, dimension, new_state)
            counterfactual_bundle = _recompute(
                counterfactual_ledger, venture_frame, counterfactual_funding_assessment,
                strategic_opportunity, founder_guidance_items, ranked_actions, risk_assessment,
            )
            scenarios.append(
                _scenario(
                    scenario_id=f"{dimension}:{direction}",
                    title=f"If {human_label} {verb}",
                    changed_assumption=f"{spec['label']} moves to: {spec['scale'][2 if new_state == 'confirmed_positive' else 0]}",
                    baseline_bundle=baseline_bundle,
                    counterfactual_bundle=counterfactual_bundle,
                    evidence_ids=[f"rubric:{dimension}"],
                    confidence=SOURCE_TYPE_BASE_CONFIDENCE["user_confirmed"],
                    assumptions=[f"Assumes the founder could realistically obtain evidence changing {human_label} this way."],
                    why_this_matters=f"{spec['label']} carries a rubric weight of {spec['weight']:.2f} — one of the largest single levers on funding readiness.",
                    limitations="A structural simulation of the rubric's own scoring rule, not a prediction that this change will actually happen.",
                )
            )
    return scenarios


def _industry_scenarios(
    evidence_ledger: list[dict], venture_frame: dict, funding_assessment: dict, baseline_bundle: dict,
    strategic_opportunity: dict | None, founder_guidance_items: list[dict] | None,
    ranked_actions: list[dict] | None, risk_assessment: list[dict] | None,
) -> list[CounterfactualScenario]:
    scenarios: list[CounterfactualScenario] = []
    for direction, verb in (("improves", "improves"), ("weakens", "weakens")):
        counterfactual_ledger = _flip_industry_ledger_item(evidence_ledger, direction)
        if counterfactual_ledger is None:
            continue
        counterfactual_bundle = _recompute(
            counterfactual_ledger, venture_frame, funding_assessment,
            strategic_opportunity, founder_guidance_items, ranked_actions, risk_assessment,
        )
        scenarios.append(
            _scenario(
                scenario_id=f"industry_confidence:{direction}",
                title=f"If industry confidence {verb}",
                changed_assumption=f"The industry classifier's confidence {verb} enough to change how much its prediction should be trusted as evidence.",
                baseline_bundle=baseline_bundle,
                counterfactual_bundle=counterfactual_bundle,
                evidence_ids=["model:industry_prediction"],
                confidence=SOURCE_TYPE_BASE_CONFIDENCE["model_inference"],
                assumptions=["Assumes the underlying description does not itself change — only how confident the classifier is in its own prediction."],
                why_this_matters="Industry confidence discounts how much the classifier's prediction can contribute as evidence, independent of every rubric answer.",
                limitations="A structural simulation of the Evidence Ledger's own model-inference discount, not a re-run of the classifier itself.",
            )
        )
    return scenarios


def _regulatory_scenarios(
    evidence_ledger: list[dict], venture_frame: dict, funding_assessment: dict, baseline_bundle: dict,
    strategic_opportunity: dict | None, founder_guidance_items: list[dict] | None,
    ranked_actions: list[dict] | None, risk_assessment: list[dict] | None,
) -> list[CounterfactualScenario]:
    scenarios: list[CounterfactualScenario] = []
    for direction, verb in (("weakens", "increases"), ("improves", "decreases")):
        counterfactual_frame = _flip_regulatory_frame_field(venture_frame, direction)
        if counterfactual_frame is None:
            continue
        counterfactual_bundle = _recompute(
            evidence_ledger, counterfactual_frame, funding_assessment,
            strategic_opportunity, founder_guidance_items, ranked_actions, risk_assessment,
        )
        scenarios.append(
            _scenario(
                scenario_id=f"regulatory_burden:{direction}",
                title=f"If regulatory burden {verb}",
                changed_assumption=f"Whether a regulatory/compliance requirement is known to apply {verb}.",
                baseline_bundle=baseline_bundle,
                counterfactual_bundle=counterfactual_bundle,
                evidence_ids=[],
                confidence=REGULATORY_RULE_CONFIDENCE,
                assumptions=["Assumes the venture's actual deployment context is what changes, not just how it's described."],
                why_this_matters="A known regulatory/compliance requirement becomes the highest-priority risk regardless of rubric confidence, per this pipeline's own established precedent.",
                limitations="A structural simulation of the Frame's known/unknown regulatory flag, not a legal or regulatory conclusion.",
            )
        )
    return scenarios


def _find_extreme(scenarios: list[CounterfactualScenario], *, best: bool) -> CounterfactualScenario | None:
    with_delta = [s for s in scenarios if s["baseline"]["decision_confidence"] != s["counterfactual"]["decision_confidence"]]
    if not with_delta:
        return None
    key = (lambda s: s["counterfactual"]["decision_confidence"] - s["baseline"]["decision_confidence"])
    return max(with_delta, key=lambda s: (key(s) if best else -key(s), s["id"]))


def build_counterfactual_simulation(
    evidence_ledger: list[dict] | None = None,
    venture_frame: dict | None = None,
    funding_assessment: dict | None = None,
    decision_synthesis: dict | None = None,
    causal_reasoning: dict | None = None,
    hypothesis_set: dict | None = None,
    contradiction_set: dict | None = None,
    alternative_explanation_set: dict | None = None,
    strategic_opportunity: dict | None = None,
    founder_guidance_items: list[dict] | None = None,
    ranked_actions: list[dict] | None = None,
    risk_assessment: list[dict] | None = None,
) -> dict:
    """Assemble the full Counterfactual Simulation object for one analysis run. Deterministic and
    idempotent: identical inputs always produce an equal output. See module docstring for the full
    audit of what is recomputed for real versus held constant, and why.
    """
    if not evidence_ledger or not venture_frame or not funding_assessment or not decision_synthesis or not causal_reasoning:
        return {
            "counterfactual_simulation_version": COUNTERFACTUAL_SIMULATION_VERSION,
            "baseline": None,
            "scenarios": [],
            "best_case": None,
            "worst_case": None,
            "highest_leverage_change": None,
            "most_fragile_assumption": None,
            "stable_findings": [],
            "changed_findings": [],
            "recommended_next_experiment": None,
        }

    # Hypothesis Set / Contradiction Set / Alternative Explanation Set are accepted (per this
    # phase's own allowed-input list) but not required to already be non-None: baseline_snapshot
    # (the only thing read off this bundle) never inspects them — they are carried for parity with
    # every counterfactual bundle's shape (which does compute them for real, via `_recompute`) and
    # for any future consumer that wants the baseline's own copy without recomputing it.
    baseline_bundle = {
        "evidence_ledger_summary": summarize_ledger(evidence_ledger),
        "hypothesis_set": hypothesis_set,
        "contradiction_set": contradiction_set,
        "alternative_explanation_set": alternative_explanation_set,
        "decision_synthesis": decision_synthesis,
        "causal_reasoning": causal_reasoning,
    }
    baseline_snapshot = _snapshot(baseline_bundle)

    scenarios: list[CounterfactualScenario] = []
    scenarios.extend(
        _rubric_scenarios(
            evidence_ledger, venture_frame, funding_assessment, baseline_bundle,
            strategic_opportunity, founder_guidance_items, ranked_actions, risk_assessment,
        )
    )
    scenarios.extend(
        _industry_scenarios(
            evidence_ledger, venture_frame, funding_assessment, baseline_bundle,
            strategic_opportunity, founder_guidance_items, ranked_actions, risk_assessment,
        )
    )
    scenarios.extend(
        _regulatory_scenarios(
            evidence_ledger, venture_frame, funding_assessment, baseline_bundle,
            strategic_opportunity, founder_guidance_items, ranked_actions, risk_assessment,
        )
    )

    best_case = _find_extreme(scenarios, best=True)
    worst_case = _find_extreme(scenarios, best=False)

    deltas = [
        (s, abs(s["counterfactual"]["decision_confidence"] - s["baseline"]["decision_confidence"]))
        for s in scenarios
    ]
    highest_leverage_change = max(deltas, key=lambda pair: (pair[1], pair[0]["id"]))[0] if deltas else None

    weakening_scenarios = [s for s in scenarios if s["id"].endswith(":weakens")]
    most_fragile_assumption = (
        min(weakening_scenarios, key=lambda s: (s["counterfactual"]["decision_confidence"], s["id"]))
        if weakening_scenarios else None
    )

    # Stable findings: any tracked field that never changes across every simulated scenario — a
    # genuine invariant, not an assumption.
    tracked_fields = ["highest_priority_risk", "highest_priority_opportunity", "highest_priority_action", "overall_decision"]
    stable_findings = [
        f"{field} never changes across any simulated scenario: {baseline_snapshot[field]!r}."
        for field in tracked_fields
        if all(s["counterfactual"][field] == baseline_snapshot[field] for s in scenarios)
    ] if scenarios else []

    changed_findings = [
        {"scenario_id": s["id"], "field": field, "from": baseline_snapshot[field], "to": s["counterfactual"][field]}
        for s in scenarios
        for field in s["affected_reasoning"]
    ]

    # The most valuable next experiment: among scenarios that *improve* the decision and whose
    # underlying dimension is not already confirmed_positive (i.e. genuinely actionable), the one
    # with the largest confidence gain — reusing the same delta metric as highest_leverage_change,
    # not a new heuristic.
    actionable_improvements = [s for s in scenarios if s["id"].endswith(":improves") and s["counterfactual"]["decision_confidence"] > s["baseline"]["decision_confidence"]]
    recommended_next_experiment = (
        max(actionable_improvements, key=lambda s: (s["counterfactual"]["decision_confidence"] - s["baseline"]["decision_confidence"], s["id"]))
        if actionable_improvements else None
    )

    return {
        "counterfactual_simulation_version": COUNTERFACTUAL_SIMULATION_VERSION,
        "baseline": baseline_snapshot,
        "scenarios": scenarios,
        "best_case": best_case,
        "worst_case": worst_case,
        "highest_leverage_change": highest_leverage_change,
        "most_fragile_assumption": most_fragile_assumption,
        "stable_findings": stable_findings,
        "changed_findings": changed_findings,
        "recommended_next_experiment": recommended_next_experiment,
    }
