"""Phase 5 (Student 3): deterministic growth/strategy planning agents with additive ML-backed
segmentation support.

These modules derive recommendations from the industry model output and the funding rubric only.
When a trained segmentation artifact is available and the caller supplied customer-level RFM
input, the customer segment module attaches a clustering-derived segment; otherwise it returns a
clear degraded non-ML fallback so the system never pretends to have a live trained model.

Additive to the existing pipeline — this module never touches judge.py's, mentor_synthesis.py's,
idea_expansion.py's, or strategic_opportunity.py's own reasoning; it only produces new, separately
namespaced planning output (see app.agents.nodes' segment_customers_node etc. and the
`student3_outputs` column).
"""

from __future__ import annotations

from app.ml.segmentation import SegmentationArtifactUnavailable, predict_customer_segment
from app.schemas.student3 import (
    CustomerSegment, GrowthItem, InnovationOpportunity, PitchSlide, RankedAction, RiskItem,
)


_DIMENSION_ACTIONS = {
    "customer_pain_evidence": ("Interview prospective customers", "high", "low", "now"),
    "market_size_evidence": ("Document a sourced market hypothesis", "high", "medium", "now"),
    "product_maturity": ("Test a narrow MVP with target users", "high", "medium", "now"),
    "traction": ("Recruit and measure a pilot cohort", "high", "medium", "now"),
    "revenue_model_clarity": ("Test a pricing and willingness-to-pay hypothesis", "high", "medium", "next"),
    "team_completeness": ("Close the highest-risk team capability gap", "medium", "high", "next"),
    "competitive_differentiation": ("Map alternatives and validate a differentiated wedge", "high", "medium", "now"),
    "problem_clarity": ("Refine the problem statement with customer language", "high", "low", "now"),
}


def customer_segment(industry: dict | None, funding: dict, *, customer_rfm: dict[str, float] | None = None) -> dict:
    """Assign a segment only when an artifact and customer-level RFM vector are available."""
    if customer_rfm is None:
        unavailable_reason = "customer RFM input was not supplied"
    else:
        try:
            prediction = predict_customer_segment(customer_rfm)
            profile = prediction["profile"]
            return CustomerSegment(
                segment_id=f"cluster_{prediction['cluster_id']}", segment_name=prediction["segment_name"],
                fit_score=None,
                characteristics=[f"Median recency: {profile['median_recency_days']:.0f} days", f"Median purchase frequency: {profile['median_frequency']:.0f}", f"Median monetary value: {profile['median_monetary']:.2f}"],
                pain_points=[], recommended_channels=[],
                evidence_basis=[f"Trained {prediction['selected_model_name']} artifact", f"Dataset version: {prediction['dataset_version']}"],
                limitations=["This assignment uses supplied customer RFM values and does not infer startup-market fit."],
                model_version=prediction["model_version"], method="clustering_model",
            ).model_dump()
        except SegmentationArtifactUnavailable as exc:
            unavailable_reason = str(exc)
    return CustomerSegment(
        segment_id="unavailable", segment_name="Customer segmentation unavailable", fit_score=None,
        characteristics=[], pain_points=[], recommended_channels=[],
        evidence_basis=["No trained customer-segment assignment was produced."], limitations=[unavailable_reason],
        model_version="unavailable", method="unavailable",
    ).model_dump()


def ranked_actions(funding: dict, industry: dict | None, segment: dict) -> list[dict]:
    missing = set(funding.get("missing_evidence", []))
    stage = funding.get("level", "unknown").replace("_", " ")
    uncertainty = bool((industry or {}).get("is_uncertain", True))
    industry_basis = (
        "Industry inference is uncertain; prioritize evidence collection before vertical-specific scaling."
        if uncertainty
        else f"Industry model inference: {(industry or {}).get('predicted_industry', 'unknown')}"
    )
    actions: list[RankedAction] = []
    for item in funding.get("breakdown", []):
        dimension = item["dimension"]
        if item.get("raw_score") == 2 or dimension not in _DIMENSION_ACTIONS:
            continue
        title, impact, effort, urgency = _DIMENSION_ACTIONS[dimension]
        score = 90 if dimension in missing else 72
        if uncertainty and dimension in {"customer_pain_evidence", "market_size_evidence", "competitive_differentiation"}:
            score = min(100, score + 5)
        if dimension == "traction" and item.get("raw_score") == 1:
            score = 96
        actions.append(
            RankedAction(
                title=title,
                priority_score=score,
                impact=impact,
                effort=effort,
                urgency=urgency,
                evidence_basis=[f"Funding rubric: {item['label']} is {item['raw_score']}/2.", f"Readiness stage: {stage}.", f"Segment: {segment['segment_name']}.", industry_basis],
                dependency="Customer evidence is required before scaling the recommendation." if dimension != "customer_pain_evidence" else "Recruit relevant interview participants.",
                readiness_dimension=dimension,
                ranking_version="next-action-rules-v1",
            )
        )
    return [item.model_dump() for item in sorted(actions, key=lambda action: action.priority_score, reverse=True)[:5]]


def innovation(industry: dict | None, funding: dict) -> list[dict]:
    domain = (industry or {}).get("predicted_industry", "the proposed domain")
    missing = funding.get("missing_evidence", [])
    opportunities = [
        InnovationOpportunity(category="feature", opportunity="Define a narrow, measurable user outcome.", rationale=f"The submission is inferred as {domain}; a focused outcome makes differentiation testable.", validation_requirement="Observe target users completing the intended workflow.", assumptions=["The submitted description identifies a recurring user problem."]),
        InnovationOpportunity(category="operational", opportunity="Design the first customer workflow for repeatable delivery.", rationale="Operational requirements are not evidenced by the short submission.", validation_requirement="Run one pilot end-to-end and document manual steps, failure modes, and handoffs.", assumptions=["A pilot workflow can be observed."]),
        InnovationOpportunity(category="defensibility", opportunity="Build defensibility from validated workflow learning, not unsupported IP claims.", rationale="No patent or proprietary-data evidence was provided.", validation_requirement="Document why users choose the workflow over named alternatives.", assumptions=["Customer feedback can be collected."]),
        InnovationOpportunity(category="ip_direction", opportunity="Maintain an invention and data-provenance log while validating the product.", rationale="This identifies possible future protection directions without claiming novelty or patentability.", validation_requirement="Seek qualified IP advice only after documenting a concrete technical contribution.", assumptions=["The team can maintain dated product records."]),
    ]
    if "product_maturity" in missing:
        opportunities.append(InnovationOpportunity(category="technical", opportunity="Prototype the smallest technical uncertainty first.", rationale="Product maturity was not evidenced in the readiness input.", validation_requirement="Run a time-boxed prototype test against one acceptance criterion.", assumptions=["A prototype is feasible with available resources."]))
    return [item.model_dump() for item in opportunities]


def risks(funding: dict, industry: dict | None) -> list[dict]:
    missing = set(funding.get("missing_evidence", []))
    definitions = [
        ("market", "Unvalidated customer problem", "customer_pain_evidence", "Interview target users before committing scope.", "Interviews do not describe a repeated costly problem."),
        ("adoption", "Unproven adoption path", "traction", "Run a bounded pilot with a clear activation event.", "Pilot participants do not reach activation."),
        ("competition", "Differentiation is not evidenced", "competitive_differentiation", "Compare the proposed workflow with alternatives in customer interviews.", "Prospects cannot explain why they would switch."),
        ("technical", "Core technical uncertainty is not evidenced", "product_maturity", "Prototype the riskiest technical assumption before broadening scope.", "The prototype cannot meet its stated acceptance criterion."),
        ("operations", "Delivery workflow is not evidenced", "product_maturity", "Document the first pilot workflow, owners, and operational handoffs.", "Pilot delivery repeatedly relies on unplanned manual work."),
        ("financial", "Pricing evidence is missing", "revenue_model_clarity", "Test willingness to pay before forecasting revenue.", "Prospects decline a pricing conversation."),
        ("regulatory_legal", "Applicable regulatory and legal obligations are unknown", "product_maturity", "Identify the product's data, geography, and sector context and obtain qualified advice where appropriate.", "A target customer requires compliance evidence the team cannot provide."),
        ("execution_team", "Execution capacity is not evidenced", "team_completeness", "Identify the capability owner for the highest-risk milestone.", "No accountable owner is named."),
        ("privacy_security", "Privacy and security requirements are unknown", "product_maturity", "Identify data handled and seek appropriate professional review where needed.", "The MVP requires sensitive data without controls."),
    ]
    result = []
    for category, title, dimension, mitigation, warning in definitions:
        absent = dimension in missing
        result.append(
            RiskItem(
                title=title,
                category=category,
                probability_band="high" if absent else "medium",
                impact_band="high" if category in {"market", "financial", "privacy_security"} else "medium",
                severity="high" if absent else "medium",
                evidence_basis=[f"Funding readiness input for {dimension}: {'missing' if absent else 'provided'}.", "No legal, security, revenue, or customer claim is inferred beyond the submitted evidence."],
                mitigation=mitigation,
                early_warning_indicator=warning,
                assumptions=["This is a planning risk, not a legal or regulatory conclusion."],
            ).model_dump()
        )
    return result


def growth_strategy(segment: dict, actions: list[dict], industry: dict | None) -> list[dict]:
    primary = actions[0]["title"] if actions else "Maintain and verify readiness evidence"
    domain = (industry or {}).get("predicted_industry", "unknown")
    channels = segment.get("recommended_channels") or []
    acquisition = (
        f"Reach {segment['segment_name']} through {channels[0].lower()}."
        if channels
        else "Evidence required: provide customer-segment or channel data before selecting an acquisition channel."
    )
    items = [
        GrowthItem(area="validation", recommendation=primary, rationale="Highest-ranked action from the readiness gaps.", dependency="A defined interview or pilot cohort.", assumptions=["Readiness inputs remain current."]),
        GrowthItem(area="acquisition", recommendation=acquisition, rationale="Channel selection requires a trained customer segment or direct channel evidence.", dependency="A testable value proposition.", assumptions=[f"The inferred industry ({domain}) is directionally useful."]),
        GrowthItem(area="partnership", recommendation="Identify one ecosystem partner that already reaches the working segment and validate mutual value before proposing a partnership.", rationale="No partnership evidence was supplied, so this is a discovery step rather than a claimed channel.", dependency="A clearly defined pilot outcome.", assumptions=["Relevant ecosystem intermediaries exist."]),
        GrowthItem(area="retention", recommendation="Define the recurring value event that should bring pilot users back, then measure it during the pilot.", rationale="No retention evidence was supplied.", dependency="An instrumented pilot workflow.", assumptions=["The product has a repeat-use case."]),
        GrowthItem(area="expansion", recommendation="Expand only after the initial segment demonstrates repeatable activation and retention.", rationale="The current segment is a hypothesis and should not be generalized prematurely.", dependency="Evidence from the initial pilot cohort.", assumptions=["The initial segment can be measured consistently."]),
        GrowthItem(area="experiment", recommendation="Run one channel test with a pre-defined activation metric and stopping rule.", rationale="No traction or conversion evidence was supplied.", dependency="Instrumented landing page, outreach, or pilot workflow.", assumptions=["A small test can be run ethically."]),
        GrowthItem(area="kpi", recommendation="Track interviews completed, activated pilots, and retained pilot users; do not report revenue until evidenced.", rationale="These measures distinguish learning from unsupported traction.", dependency="A consistent event definition.", assumptions=["Pilot users consent to measurement."]),
    ]
    return [item.model_dump() for item in items]


def pitch_deck(name: str, description: str, industry: dict | None, funding: dict, segment: dict, actions: list[dict]) -> list[dict]:
    domain = (industry or {}).get("predicted_industry", "unknown")
    next_milestone = actions[0]["title"] if actions else "evidence required"
    channels = segment.get("recommended_channels") or []
    go_to_market = f"Start with {channels[0].lower()} for the trained segment." if channels else "Evidence required: a trained segment assignment or channel test result."
    slides = [
        PitchSlide(title="Title", content=[name, description], evidence_status="verified evidence"),
        PitchSlide(title="Problem", content=["Problem framing is based on the submitted description.", "Evidence required: customer interviews confirming frequency and cost."], evidence_status="evidence required"),
        PitchSlide(title="Solution", content=[description], evidence_status="verified evidence"),
        PitchSlide(title="Market", content=[f"Industry model inference: {domain}.", "Unknown: market size; do not add a number without a source."], evidence_status="model inference"),
        PitchSlide(title="Customer", content=[f"Working segment: {segment['segment_name']}.", "Validate this segment before using it as a market fact."], evidence_status="deterministic assessment"),
        PitchSlide(title="Product", content=["Evidence required: a demonstrable MVP or prototype outcome."], evidence_status="evidence required"),
        PitchSlide(title="Differentiation", content=["Evidence required: comparison with the alternatives customers use today."], evidence_status="evidence required"),
        PitchSlide(title="Business Model", content=["Unknown: no pricing or unit-economics evidence was supplied."], evidence_status="unknown"),
        PitchSlide(title="Traction and evidence", content=["Unknown: no revenue, customers, or partnerships were supplied.", f"Next evidence milestone: {next_milestone}."], evidence_status="unknown"),
        PitchSlide(title="Go-to-Market", content=[go_to_market, "Evidence required: channel activation results."], evidence_status="evidence required" if not channels else "deterministic assessment"),
        PitchSlide(title="Competition", content=["Evidence required: named alternatives and customer switching rationale."], evidence_status="evidence required"),
        PitchSlide(title="Financial Outlook", content=["Unknown: no revenue, cost, pricing, or forecast evidence was supplied."], evidence_status="unknown"),
        PitchSlide(title="Risks and next milestone", content=["Address readiness gaps before making a funding ask.", f"Current readiness assessment: {funding.get('overall_score', 0)}/100 (deterministic rubric)."], evidence_status="deterministic assessment"),
        PitchSlide(title="Team", content=["Evidence required: team roles and capability coverage were not supplied."], evidence_status="evidence required"),
        PitchSlide(title="Funding Ask or Next Milestone", content=[f"Next milestone: {next_milestone}.", "Unknown: no funding ask was supplied."], evidence_status="unknown"),
        PitchSlide(title="Closing Vision", content=["Assumption: the submitted problem can be validated with a focused early-adopter workflow."], evidence_status="assumption"),
        PitchSlide(title="Executive Summary", content=[f"{name}: validate the stated problem with {segment['segment_name']} before claiming traction or market size."], evidence_status="deterministic assessment"),
        PitchSlide(title="Demo Script", content=["Show the target user's current problem, the smallest proposed workflow, and the observable outcome to validate."], evidence_status="assumption"),
    ]
    return [item.model_dump() for item in slides]
