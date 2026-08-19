"""Causal Reasoning Engine — VentureForge Intelligence Architecture, Phase H.

MISSION. Every prior phase reports a conclusion (a hypothesis, a contradiction, a decision). None of
them explains *why* one thing leads to another in an explicit, inspectable structure — that
reasoning has, until now, lived only inside narrative sentences. This module is the one canonical
place that represents "cause leads to effect" as data (`CauseEffectChain`), not prose.

========================================================================================
FIRST — audit of causal language already in the repository (`because`, `therefore`, `leads to`,
`results in`, `causes`, `creates`, `increases`, `reduces`, `improves`, `weakens`, `blocks`, `depends
on`), and how each is classified:

  - `app.agents.mentor_synthesis` ("Everything you build after this depends on these answers...",
    "that foundation is what everything else here depends on.") — **Template wording.** Fixed
    narrative sentences used for roadmap framing, not derived from any specific evidence pair. Left
    exactly as-is (no existing output changes, per this phase's own rule); the new engine now
    provides the structural version of this same idea (`highest_priority_action` chains, below)
    additively, without touching this prose.
  - `app.agents.business_model_agent` ("...how far it scales still depends on channels and costs
    you haven't validated yet.") — **Template wording.** A generic, always-emitted sentence, not
    keyed to a specific evidence id. Left as-is for the same reason.
  - `app.agents.strategic_opportunity` ("Depends on capabilities beyond what's confirmed present
    today.") — **Correlation dressed as causal.** `feature_gap.premature_capabilities` and a
    `future_expansion` item co-occur, but no explicit mechanism/evidence link was ever represented.
    This is exactly the gap Phase H closes structurally (see `_competition_to_differentiation` and
    the rubric-dimension chains below use the same underlying Venture Frame fields this sentence
    gestures at, now with explicit evidence ids and a disclosed strength label).
  - `app.agents.founder_guidance` ("[Segment] loses/wastes [specific cost] because [problem].") —
    **Not the system's own claim.** This is a fill-in-the-blank *template the founder is prompted to
    complete themselves* (see the surrounding `discovery_question` guidance), not an assertion
    VentureForge makes about the venture. Out of scope for this audit.
  - `app.agents.hypothesis_set` ("...held open because {reason}") — **True causal reasoning**,
    already structurally represented (the `reason` field is itself evidence-derived, from
    `is_ambiguous`). Not migrated; already the correct pattern this phase generalizes.
  - `app.ml.funding_readiness` (`weighted_contribution` per rubric dimension) — **True causal
    reasoning, already fully mechanical and disclosed** — a dimension's confirmed answer contributes
    an exact, already-computed number of points to `overall_score`, which maps to `level` via fixed
    thresholds. This is the strongest, most defensible source of causal chains in the whole
    pipeline (see `_rubric_dimension_chains`): the "mechanism" is the rubric's own arithmetic, not an
    inference this module invents.

No other module in the repository independently generates a cause-effect claim structurally (only in
prose, as audited above); there is nothing to delete, since the only pre-existing structural
candidate (`hypothesis_set`'s `is_ambiguous`-derived `reason`) is already correct and is reused,
never duplicated (see `_regulatory_or_rubric_risk_chain`, which reads `decision_synthesis`'s already-
resolved `highest_priority_risk` rather than re-deriving the regulatory-vs-rubric precedence rule a
second time).

========================================================================================
SECOND/THIRD — one canonical module, consuming only: Evidence Ledger (via evidence ids already
carried on Hypothesis Set / Decision Synthesis fields — never re-read directly), Venture Frame,
Hypothesis Set (indirectly, through Decision Synthesis), Contradiction Set (indirectly, through
Decision Synthesis's `remaining_uncertainties`), Alternative Explanation Set (indirectly, through
Decision Synthesis), **Decision Synthesis** (directly — this is the key design decision, explained
next), Funding Assessment, Strategic Opportunity, Founder Guidance Items. Student 3 outputs are
consumed only via Decision Synthesis's already-resolved `highest_priority_risk`/`highest_priority_
action` (see below) — never re-read raw, to avoid re-deriving Phase I's own precedence logic.
Nothing here reads `startup_description` or calls a model/LLM.

THE KEY DESIGN DECISION: build chains from Decision Synthesis's *resolved* fields, not from raw
inputs a second time. Phase I (`decision_synthesis.py`) already reasoned across every module to pick
the single `highest_priority_opportunity`/`highest_priority_risk`/`highest_priority_action` —
including the regulatory-outranks-rubric-risk precedent and the ranked-actions-vs-founder-guidance
fallback order. Re-deriving any of that here to build a "risk chain" would be exactly the "parallel
causal system" this phase's SELF REVIEW forbids. Instead, this module treats Decision Synthesis's
resolved answer as the *effect side* of a chain and explains, structurally, what produced it — i.e.
Causal Reasoning explains Decision Synthesis, it does not recompute it. The only genuinely new
evidence sources this module reads directly (because Decision Synthesis does not already surface
them) are: `funding_assessment.breakdown`'s `weighted_contribution` (the rubric's own mechanical
math — see FIRST above), and Venture Frame's `competition`/`differentiation`/`venture_stage` fields
cross-referenced against Strategic Opportunity's `primary_opportunity.suitable_stage`.

CAUSAL DOMAINS FROM THE BRIEF — coverage and honest gaps:
  - "Evidence Quality -> Decision Confidence": implemented (`_evidence_quality_chain`) — the
    flagship chain; it is literally Decision Synthesis's own `propagate_confidence` computation
    restated as an explicit chain.
  - "Business Model -> Funding Readiness", "Founder Capability -> Execution Risk" (via
    `team_completeness`), general dimension-level chains: implemented (`_rubric_dimension_chains`),
    using the rubric's own disclosed `weighted_contribution`.
  - "Regulation -> Execution Risk": implemented, but *through* Decision Synthesis's already-resolved
    `highest_priority_risk` (see `_highest_priority_risk_chain`) rather than re-detecting the
    regulatory hypothesis a second time.
  - "Competition -> Differentiation": implemented (`_competition_to_differentiation_chain`), the one
    genuinely new cross-Frame-field connection this module adds.
  - "Market Timing -> Opportunity": implemented (`_venture_stage_to_opportunity_fit_chain`), labeled
    `"correlation_only"` — a stage-match comparison, not an arithmetic mechanism.
  - "Customer -> Validation", "Customer -> Growth": partially covered — `customer_pain_evidence` and
    `traction` each get their own mechanical rubric chain (customer evidence -> funding readiness);
    a dedicated "Customer -> Growth" chain is **not implemented** because no structured evidence
    field measures growth as a distinct concept from `traction`/`revenue_model_clarity` (already
    covered) without fabricating a new signal.
  - "Pricing -> Adoption", "Pricing -> Unit Economics", "Distribution -> Traction": **not
    implemented.** No input in this phase's allowed list (`revenue_estimate`, a distinct
    "distribution" evidence field) carries pricing/distribution evidence independent of what
    `revenue_model_clarity`/`traction` already represent — inventing a link here would mean either
    reading an input outside this phase's mandated list or fabricating a signal that doesn't exist.
    Documented as a limitation, not silently skipped.

Every chain answers, in its own fields: why did this happen (`cause`), why does it matter (`effect`
+ `intermediate_steps`), what evidence supports it (`evidence_ids`), what assumption is required
(`assumptions`), what would make it collapse (`what_breaks_this_chain`), and what would strengthen it
(`what_strengthens_this_chain`).

STRENGTH LABELING (disclosed, four values, never invented per-chain):
  - `"strong"`: a literal, already-computed arithmetic mechanism ties cause to effect (the rubric's
    own `weighted_contribution`, or Decision Synthesis's own `propagate_confidence` output).
  - `"moderate"`: a real, evidence-linked but non-arithmetic mechanism (e.g. Decision Synthesis
    already selected this as the highest-priority risk/opportunity from a non-ledger source such as
    Strategic Opportunity or Student 3's fixed risk taxonomy).
  - `"correlation_only"`: both sides are independently evidenced but no mechanism ties them beyond
    co-occurrence/alignment (e.g. venture stage vs. a suggested suitable stage).
  - `"unknown"`: never assigned to an emitted chain — if a candidate chain's evidence is
    insufficient to assert even a correlation, no chain is emitted for it at all (see `remaining_
    uncertainties`, which is where genuinely unresolved/unknown material already lives, via Decision
    Synthesis).

NEVER INVENT CAUSALITY: every chain builder below returns `None`/is skipped whenever its required
Frame/Assessment/Decision-Synthesis fields are not both known — mirroring the same non-fabrication
discipline every prior phase in this architecture already applies.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from app.agents.confidence_engine import propagate_confidence
from app.agents.venture_frame import is_known

CAUSAL_REASONING_VERSION = "v1"

Strength = Literal["strong", "moderate", "correlation_only", "unknown"]

_DIMENSION_CAUSE_LABELS: dict[str, str] = {
    "problem_clarity": "Problem Clarity",
    "customer_pain_evidence": "Customer Validation",
    "market_size_evidence": "Market Evidence",
    "product_maturity": "Product Maturity",
    "traction": "Distribution & Traction",
    "revenue_model_clarity": "Business Model Clarity",
    "team_completeness": "Founder Capability",
    "competitive_differentiation": "Competitive Differentiation",
}


class CauseEffectChain(TypedDict):
    id: str
    title: str
    cause: str
    effect: str
    confidence: float
    evidence_ids: list[str]
    assumptions: list[str]
    intermediate_steps: list[str]
    strength: Strength
    limitations: str
    what_breaks_this_chain: str
    what_strengthens_this_chain: str


def _chain(
    chain_id: str, cause: str, effect: str, confidence: float, evidence_ids: list[str], assumptions: list[str],
    intermediate_steps: list[str], strength: Strength, limitations: str,
    what_breaks_this_chain: str, what_strengthens_this_chain: str,
) -> CauseEffectChain:
    return {
        "id": chain_id,
        "title": f"{cause} → {effect}",
        "cause": cause,
        "effect": effect,
        "confidence": round(confidence, 4),
        "evidence_ids": list(evidence_ids),
        "assumptions": list(assumptions),
        "intermediate_steps": list(intermediate_steps),
        "strength": strength,
        "limitations": limitations,
        "what_breaks_this_chain": what_breaks_this_chain,
        "what_strengthens_this_chain": what_strengthens_this_chain,
    }


def _evidence_quality_chain(decision_synthesis: dict | None) -> CauseEffectChain | None:
    if not decision_synthesis:
        return None
    confidence = decision_synthesis.get("decision_confidence")
    if confidence is None:
        return None
    unresolved = [u for u in decision_synthesis.get("remaining_uncertainties", []) if u["kind"] != "missing_information"]
    steps = [
        f"Evidence combines (via the Confidence Engine's noisy-OR + propagation rules) to {decision_synthesis['decision_confidence_label']} confidence ({confidence:.2f}).",
    ]
    if unresolved:
        steps.append(f"{len(unresolved)} still-open contradiction(s)/ambiguity(-ies) were folded in, each lowering confidence proportionally to how confident we are the conflict is real.")
    else:
        steps.append("No unresolved contradiction currently discounts this confidence.")
    steps.append("That combined confidence is what every downstream recommendation in this analysis is scaled against.")
    return _chain(
        chain_id="evidence_quality->decision_confidence",
        cause="Evidence Quality & Completeness",
        effect="Decision Confidence",
        confidence=confidence,
        evidence_ids=list(dict.fromkeys(decision_synthesis.get("supporting_evidence", []) + decision_synthesis.get("conflicting_evidence", []))),
        assumptions=["Assumes every evidence item's source-type confidence prior still accurately reflects how much that kind of evidence should be trusted."],
        intermediate_steps=steps,
        strength="strong",
        limitations="This is a confidence-in-the-current-picture measure, not a probability that the venture will succeed.",
        what_breaks_this_chain="Any of the supporting evidence turning out to be inaccurate, or a new contradiction emerging that the Contradiction Engine hasn't seen yet.",
        what_strengthens_this_chain="Resolving any still-open contradiction, or adding an independent, corroborating piece of evidence.",
    )


def _rubric_dimension_chains(funding_assessment: dict | None) -> list[CauseEffectChain]:
    if not funding_assessment or "breakdown" not in funding_assessment:
        return []
    breakdown = funding_assessment["breakdown"]
    overall_score = funding_assessment.get("overall_score", 0.0)
    level = funding_assessment.get("level", "unknown")
    chains: list[CauseEffectChain] = []
    for entry in breakdown:
        state = entry.get("state")
        if state not in ("confirmed_positive", "confirmed_negative"):
            continue
        dimension = entry["dimension"]
        cause_label = _DIMENSION_CAUSE_LABELS.get(dimension, entry["label"])
        contribution = entry.get("weighted_contribution", 0.0)
        weight = entry.get("weight", 0.0)
        direction = "supports" if state == "confirmed_positive" else "limits"
        chains.append(
            _chain(
                chain_id=f"rubric:{dimension}->funding_readiness",
                cause=cause_label,
                effect="Funding Readiness",
                confidence=0.9,  # user_confirmed base prior (SOURCE_TYPE_BASE_CONFIDENCE) — the rubric answer is a direct founder confirmation, not an inference.
                evidence_ids=[f"rubric:{dimension}"],
                assumptions=[f"Assumes the founder's answer for {entry['label']} is still accurate."],
                intermediate_steps=[
                    f"The founder confirmed: {entry['scale_description']}",
                    f"This {direction} the overall funding-readiness score: {contribution:.2f} of {overall_score:.2f} points, at a rubric weight of {weight:.2f}.",
                    f"The overall score currently maps to the '{level}' readiness level.",
                ],
                strength="strong",
                limitations="Reflects this rubric's own fixed weighting scheme, not an external investor's judgment.",
                what_breaks_this_chain=f"If the founder's answer for {entry['label']} changes, this exact contribution changes with it.",
                what_strengthens_this_chain=f"Independent evidence corroborating {entry['label']} beyond the founder's own answer.",
            )
        )
    return chains


def _highest_priority_opportunity_chain(decision_synthesis: dict | None) -> CauseEffectChain | None:
    opportunity = (decision_synthesis or {}).get("highest_priority_opportunity")
    if not opportunity:
        return None
    strength: Strength = "strong" if opportunity.get("source") == "evidence_ledger" else "moderate"
    confidence = opportunity.get("confidence")
    if confidence is None:
        confidence = propagate_confidence(decision_synthesis.get("decision_confidence", 0.0))
    return _chain(
        chain_id="highest_priority_opportunity->decision",
        cause=opportunity["title"],
        effect="Overall Decision",
        confidence=confidence,
        evidence_ids=list(opportunity.get("supporting_evidence_ids", [])),
        assumptions=[opportunity.get("note", "Assumes this opportunity remains available as the venture evolves.")],
        intermediate_steps=[
            opportunity["description"],
            "This is the single highest-priority opportunity Decision Synthesis selected after reasoning across every module.",
        ],
        strength=strength,
        limitations="One selected opportunity among possibly several — see alternative_decisions on Decision Synthesis for others considered.",
        what_breaks_this_chain="The underlying evidence for this opportunity being contradicted or withdrawn.",
        what_strengthens_this_chain="Independent corroboration from another module naming the same opportunity (see corroborated_by).",
    )


def _highest_priority_risk_chain(decision_synthesis: dict | None) -> CauseEffectChain | None:
    risk = (decision_synthesis or {}).get("highest_priority_risk")
    if not risk:
        return None
    source_strength: dict[str, Strength] = {
        "evidence_ledger": "strong",
        "contradiction_set": "moderate",
        "strategic_opportunity": "moderate",
        "student3_risk_assessment": "moderate",
    }
    strength = source_strength.get(risk.get("source"), "moderate")
    confidence = risk.get("confidence")
    if confidence is None:
        confidence = 1.0 - decision_synthesis.get("decision_confidence", 0.0)
    return _chain(
        chain_id="highest_priority_risk->execution_risk",
        cause=risk["title"],
        effect="Execution Risk",
        confidence=confidence,
        evidence_ids=list(risk.get("supporting_evidence_ids", [])),
        assumptions=["Assumes this risk remains unaddressed at the time this analysis is read."],
        intermediate_steps=[
            risk["description"],
            risk.get("reason_ranked_first", "Selected as the single highest-priority risk after reasoning across every module."),
        ],
        strength=strength,
        limitations="A planning risk, not a legal, financial, or regulatory conclusion.",
        what_breaks_this_chain="The founder resolving or providing new evidence for this specific risk.",
        what_strengthens_this_chain="This risk remaining unaddressed in a later evidence update.",
    )


def _highest_priority_action_chain(decision_synthesis: dict | None, founder_guidance_items: list[dict] | None) -> CauseEffectChain | None:
    action = (decision_synthesis or {}).get("highest_priority_action")
    if not action:
        return None
    goal = (decision_synthesis or {}).get("highest_validation_goal") or (decision_synthesis or {}).get("highest_learning_goal")
    effect = goal["title"] if goal else "Reduced Overall Uncertainty"
    why_it_matters = goal.get("why_it_matters") if goal else None
    if why_it_matters is None:
        # Only meaningful when the action itself came from founder_guidance_items (in which case
        # `action["title"]` is literally that item's own `next_step` text) — a ranked_actions-sourced
        # action's title uses different wording and would never match, so skip the lookup rather
        # than attempt a comparison that can only spuriously succeed or silently fail.
        matching = (
            next((g for g in (founder_guidance_items or []) if g.get("next_step") == action["title"]), None)
            if action.get("source") == "founder_guidance_items"
            else None
        )
        why_it_matters = matching.get("why_it_matters") if matching else "Addressing the single highest-priority action available right now."
    return _chain(
        chain_id="highest_priority_action->uncertainty_reduction",
        cause=action["title"],
        effect=effect,
        # A planned action has not yet produced observed evidence — its confidence is capped at how
        # much we trust the overall picture that selected it as the priority (decision_confidence),
        # never higher, reusing the Confidence Engine's own number rather than an invented constant.
        confidence=(decision_synthesis or {}).get("decision_confidence", 0.0),
        evidence_ids=[],
        assumptions=["Assumes this action is actually carried out and observed, not just planned."],
        intermediate_steps=[action.get("description") or "", why_it_matters],
        strength="moderate",
        limitations="Describes an intended effect of a planned action, not an already-observed outcome.",
        what_breaks_this_chain="The action being carried out but not producing the expected evidence.",
        what_strengthens_this_chain="Completing this action and recording the resulting evidence in a future analysis.",
    )


def _competition_to_differentiation_chain(venture_frame: dict | None) -> CauseEffectChain | None:
    venture_frame = venture_frame or {}
    competition = venture_frame.get("competition")
    differentiation = venture_frame.get("differentiation")
    if not competition or not differentiation or not is_known(competition) or not is_known(differentiation):
        return None
    confidence = propagate_confidence(competition["confidence"], differentiation["confidence"])
    return _chain(
        chain_id="competition->differentiation",
        cause="Named Competition",
        effect="Competitive Differentiation",
        confidence=confidence,
        evidence_ids=list(dict.fromkeys(competition["evidence_ids"] + differentiation["evidence_ids"])),
        assumptions=["Assumes the named competitors remain the venture's real point of comparison as the market evolves."],
        intermediate_steps=[
            f"Named alternatives are on record: {competition['supporting_text']}",
            f"Differentiation evidence: {differentiation['supporting_text'] or differentiation['value']}",
            "Both facts are known at once, but no formula here proves one caused the other — only that they co-occur in the current evidence.",
        ],
        strength="correlation_only",
        limitations="Co-occurrence, not a proven mechanism — differentiation could exist independently of the named competitors.",
        what_breaks_this_chain="A named competitor turning out not to be a real alternative after all.",
        what_strengthens_this_chain="A direct customer comparison confirming the differentiation holds against these specific named competitors.",
    )


def _venture_stage_to_opportunity_fit_chain(venture_frame: dict | None, strategic_opportunity: dict | None) -> CauseEffectChain | None:
    venture_frame = venture_frame or {}
    stage_field = venture_frame.get("venture_stage")
    primary_opportunity = (strategic_opportunity or {}).get("primary_opportunity")
    if not stage_field or not is_known(stage_field) or not primary_opportunity or not primary_opportunity.get("suitable_stage"):
        return None
    stage = stage_field["value"]
    suitable_stage = primary_opportunity["suitable_stage"]
    aligned = str(stage) == str(suitable_stage)
    return _chain(
        chain_id="venture_stage->opportunity_fit",
        cause="Venture Stage",
        effect="Opportunity Timing Fit",
        confidence=stage_field["confidence"],
        evidence_ids=list(stage_field["evidence_ids"]),
        assumptions=["Assumes the founder's stated stage still accurately reflects where the venture is today."],
        intermediate_steps=[
            f"The founder's stated stage is '{stage}'.",
            f"The primary opportunity's suitable stage is '{suitable_stage}'.",
            "These stages match, which is a timing alignment, not a guarantee of market timing." if aligned
            else "These stages do not currently match, which is a timing gap worth noting, not a proven barrier.",
        ],
        strength="correlation_only",
        limitations="A stage-label comparison only — it does not measure real market demand or timing.",
        what_breaks_this_chain="The venture reaching a later stage without the opportunity's suitable stage changing accordingly.",
        what_strengthens_this_chain="The venture's stage and the opportunity's suitable stage continuing to move together.",
    )


def _detect_cycle(edges: list[tuple[str, str]]) -> bool:
    graph: dict[str, list[str]] = {}
    for source, target in edges:
        graph.setdefault(source, []).append(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for neighbor in graph.get(node, []):
            if _visit(neighbor):
                return True
        visiting.discard(node)
        visited.add(node)
        return False

    return any(_visit(node) for node in list(graph.keys()))


def _build_causal_graph(chains: list[CauseEffectChain]) -> dict:
    nodes = sorted({c["cause"] for c in chains} | {c["effect"] for c in chains})
    edges = [{"from": c["cause"], "to": c["effect"], "chain_id": c["id"]} for c in chains]
    has_cycle = _detect_cycle([(e["from"], e["to"]) for e in edges])
    out_degree: dict[str, int] = {}
    for edge in edges:
        out_degree[edge["from"]] = out_degree.get(edge["from"], 0) + 1
    return {"nodes": nodes, "edges": edges, "has_cycle": has_cycle, "out_degree": out_degree}


_STRENGTH_RANK: dict[Strength, int] = {"strong": 3, "moderate": 2, "correlation_only": 1, "unknown": 0}


def build_causal_reasoning(
    decision_synthesis: dict | None = None,
    venture_frame: dict | None = None,
    funding_assessment: dict | None = None,
    strategic_opportunity: dict | None = None,
    founder_guidance_items: list[dict] | None = None,
) -> dict:
    """Assemble the one canonical Causal Reasoning object for an analysis run. Deterministic and
    idempotent: identical inputs always produce an equal output. See module docstring for the full
    audit of what is reused (Decision Synthesis's own resolved fields) versus what is newly reasoned
    (the rubric's own mechanical weighting, and the two genuinely new Venture Frame cross-checks).
    """
    candidates = [
        _evidence_quality_chain(decision_synthesis),
        *_rubric_dimension_chains(funding_assessment),
        _highest_priority_opportunity_chain(decision_synthesis),
        _highest_priority_risk_chain(decision_synthesis),
        _highest_priority_action_chain(decision_synthesis, founder_guidance_items),
        _competition_to_differentiation_chain(venture_frame),
        _venture_stage_to_opportunity_fit_chain(venture_frame, strategic_opportunity),
    ]
    chains: list[CauseEffectChain] = []
    seen_ids: set[str] = set()
    for chain in candidates:
        if chain is None or chain["id"] in seen_ids:
            continue
        seen_ids.add(chain["id"])
        chains.append(chain)

    if not chains:
        return {
            "causal_reasoning_version": CAUSAL_REASONING_VERSION,
            "primary_chain": None,
            "secondary_chains": [],
            "causal_graph": {"nodes": [], "edges": [], "has_cycle": False, "out_degree": {}},
            "critical_dependencies": [],
            "weakest_link": None,
            "highest_leverage_point": None,
            "highest_uncertainty": None,
        }

    primary = chains[0]
    secondary = chains[1:]

    graph = _build_causal_graph(chains)

    critical_dependencies: list[str] = []
    for chain in chains:
        for assumption in chain["assumptions"]:
            if assumption not in critical_dependencies:
                critical_dependencies.append(assumption)

    weakest_link = min(chains, key=lambda c: (c["confidence"], c["id"]))

    leverage_candidates = [c for c in chains if graph["out_degree"].get(c["cause"], 0) >= 1]
    highest_leverage_point = max(
        leverage_candidates, key=lambda c: (graph["out_degree"].get(c["cause"], 0), -_STRENGTH_RANK[c["strength"]], c["id"])
    ) if leverage_candidates else primary

    uncertain_candidates = [c for c in chains if c["strength"] in ("correlation_only", "unknown")]
    highest_uncertainty = min(uncertain_candidates, key=lambda c: (c["confidence"], c["id"])) if uncertain_candidates else weakest_link

    return {
        "causal_reasoning_version": CAUSAL_REASONING_VERSION,
        "primary_chain": primary,
        "secondary_chains": secondary,
        "causal_graph": graph,
        "critical_dependencies": critical_dependencies,
        "weakest_link": weakest_link,
        "highest_leverage_point": highest_leverage_point,
        "highest_uncertainty": highest_uncertainty,
    }
