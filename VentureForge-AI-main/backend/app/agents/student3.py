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

from app.agents.venture_vocabulary import with_article
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
        "I'm not confident yet which industry this fits, so I'd focus on general evidence-gathering "
        "before anything industry-specific."
        if uncertainty
        else f"This fits what I'm already reading as {with_article((industry or {}).get('predicted_industry', 'unclear').replace('_', ' '))} venture."
    )
    has_segment = segment.get("segment_name") not in (None, "Customer segmentation unavailable")
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
                evidence_basis=[
                    f"You haven't confirmed {item['label'].lower()} yet — that's exactly why this is worth doing next.",
                    f"You're at the {stage} stage right now, which is exactly when this matters most.",
                    f"This fits {segment['segment_name'].lower()}." if has_segment else "No specific customer segment is confirmed yet, so this applies broadly.",
                    industry_basis,
                ],
                dependency="Get real customer evidence before you scale this." if dimension != "customer_pain_evidence" else "Recruit relevant interview participants.",
                readiness_dimension=dimension,
                ranking_version="next-action-rules-v1",
            )
        )
    return [item.model_dump() for item in sorted(actions, key=lambda action: action.priority_score, reverse=True)[:5]]


def innovation(industry: dict | None, funding: dict) -> list[dict]:
    domain = (industry or {}).get("predicted_industry", "").replace("_", " ") or "your space"
    missing = funding.get("missing_evidence", [])
    opportunities = [
        InnovationOpportunity(category="feature", opportunity="Define a narrow, measurable user outcome.", rationale=f"You're building in what I'm reading as {domain} — a focused outcome is what will make your differentiation actually testable.", validation_requirement="Observe target users completing the intended workflow.", assumptions=["The submitted description identifies a recurring user problem."]),
        InnovationOpportunity(category="operational", opportunity="Design the first customer workflow for repeatable delivery.", rationale="You haven't shown me yet how this actually gets delivered day-to-day — that's worth designing before you scale.", validation_requirement="Run one pilot end-to-end and document manual steps, failure modes, and handoffs.", assumptions=["A pilot workflow can be observed."]),
        InnovationOpportunity(category="defensibility", opportunity="Build defensibility from validated workflow learning, not unsupported IP claims.", rationale="You haven't shown me a patent or proprietary data yet, and that's fine — real defensibility usually comes from what you learn running the workflow, not a claim on paper.", validation_requirement="Document why users choose the workflow over named alternatives.", assumptions=["Customer feedback can be collected."]),
        InnovationOpportunity(category="ip_direction", opportunity="Maintain an invention and data-provenance log while validating the product.", rationale="This just keeps your future options open — it's not a claim that anything here is novel or patentable yet.", validation_requirement="Seek qualified IP advice only after documenting a concrete technical contribution.", assumptions=["The team can maintain dated product records."]),
    ]
    if "product_maturity" in missing:
        opportunities.append(InnovationOpportunity(category="technical", opportunity="Prototype the smallest technical uncertainty first.", rationale="You haven't shown me a working prototype yet — proving the riskiest technical piece first is the cheapest way to find out if this works.", validation_requirement="Run a time-boxed prototype test against one acceptance criterion.", assumptions=["A prototype is feasible with available resources."]))
    return [item.model_dump() for item in opportunities]


def risks(funding: dict, industry: dict | None) -> list[dict]:
    missing = set(funding.get("missing_evidence", []))
    definitions = [
        ("market", "You haven't confirmed this problem is real yet", "customer_pain_evidence", "Interview target users before committing scope.", "Interviews do not describe a repeated costly problem."),
        ("adoption", "It's not yet proven people will actually adopt this", "traction", "Run a bounded pilot with a clear activation event.", "Pilot participants do not reach activation."),
        ("competition", "Your differentiation isn't proven yet", "competitive_differentiation", "Compare the proposed workflow with alternatives in customer interviews.", "Prospects cannot explain why they would switch."),
        ("technical", "There's a core technical uncertainty you haven't resolved", "product_maturity", "Prototype the riskiest technical assumption before broadening scope.", "The prototype cannot meet its stated acceptance criterion."),
        ("operations", "How you'll actually deliver this isn't proven yet", "product_maturity", "Document the first pilot workflow, owners, and operational handoffs.", "Pilot delivery repeatedly relies on unplanned manual work."),
        ("financial", "You don't have pricing evidence yet", "revenue_model_clarity", "Test willingness to pay before forecasting revenue.", "Prospects decline a pricing conversation."),
        ("regulatory_legal", "You haven't confirmed what regulatory or legal obligations apply", "product_maturity", "Identify the product's data, geography, and sector context and obtain qualified advice where appropriate.", "A target customer requires compliance evidence the team cannot provide."),
        ("execution_team", "It's not yet clear your team can execute this", "team_completeness", "Identify the capability owner for the highest-risk milestone.", "No accountable owner is named."),
        ("privacy_security", "You haven't worked out your privacy and security needs yet", "product_maturity", "Identify data handled and seek appropriate professional review where needed.", "The MVP requires sensitive data without controls."),
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
                evidence_basis=[
                    "You haven't given me evidence on this yet." if absent else "You've already given me evidence here — worth keeping current as you learn more.",
                    "I'm not inferring any legal, security, revenue, or customer claim beyond what you've actually submitted.",
                ],
                mitigation=mitigation,
                early_warning_indicator=warning,
                assumptions=["This is a planning risk, not a legal or regulatory conclusion."],
            ).model_dump()
        )
    return result


def growth_strategy(segment: dict, actions: list[dict], industry: dict | None) -> list[dict]:
    primary = actions[0]["title"] if actions else "Keep confirming your readiness evidence is still current"
    domain = (industry or {}).get("predicted_industry", "").replace("_", " ") or "your space"
    channels = segment.get("recommended_channels") or []
    acquisition = (
        f"Reach {segment['segment_name']} through {channels[0].lower()}."
        if channels
        else "You haven't given me a customer segment or channel yet — that's what to nail down before picking how you'll acquire customers."
    )
    items = [
        GrowthItem(area="validation", recommendation=primary, rationale="This is your highest-priority open question right now.", dependency="A defined interview or pilot cohort.", assumptions=["Readiness inputs remain current."]),
        GrowthItem(area="acquisition", recommendation=acquisition, rationale="Picking a channel with confidence needs either a trained customer segment or real channel evidence — you don't have either yet.", dependency="A testable value proposition.", assumptions=[f"Being in {domain} is directionally useful context."]),
        GrowthItem(area="partnership", recommendation="Identify one ecosystem partner that already reaches the working segment and validate mutual value before proposing a partnership.", rationale="You haven't shown me partnership evidence yet, so this is worth exploring, not something to bank on.", dependency="A clearly defined pilot outcome.", assumptions=["Relevant ecosystem intermediaries exist."]),
        GrowthItem(area="retention", recommendation="Define the recurring value event that should bring pilot users back, then measure it during the pilot.", rationale="You haven't shown me retention evidence yet — that's the next thing worth defining.", dependency="An instrumented pilot workflow.", assumptions=["The product has a repeat-use case."]),
        GrowthItem(area="expansion", recommendation="Expand only after the initial segment demonstrates repeatable activation and retention.", rationale="Your current segment is still a hypothesis — proving it first keeps you from over-extending too soon.", dependency="Evidence from the initial pilot cohort.", assumptions=["The initial segment can be measured consistently."]),
        GrowthItem(area="experiment", recommendation="Run one channel test with a pre-defined activation metric and stopping rule.", rationale="You haven't shown me traction or conversion evidence yet, so a small, bounded test is the right next step.", dependency="Instrumented landing page, outreach, or pilot workflow.", assumptions=["A small test can be run ethically."]),
        GrowthItem(area="kpi", recommendation="Track interviews completed, activated pilots, and retained pilot users; hold off on reporting revenue until it's real.", rationale="These are the numbers that show you're actually learning, not just staying busy.", dependency="A consistent event definition.", assumptions=["Pilot users consent to measurement."]),
    ]
    return [item.model_dump() for item in items]


def pitch_deck(name: str, description: str, industry: dict | None, funding: dict, segment: dict, actions: list[dict]) -> list[dict]:
    domain = (industry or {}).get("predicted_industry", "").replace("_", " ") or "an unclear space"
    next_milestone = actions[0]["title"] if actions else "closing your next evidence gap"
    channels = segment.get("recommended_channels") or []
    has_segment = segment.get("segment_name") not in (None, "Customer segmentation unavailable")
    go_to_market = (
        f"Start with {channels[0].lower()} for {segment['segment_name'].lower()}."
        if channels
        else "You haven't confirmed a segment or channel yet — that's the next thing to test, not something to guess at here."
    )
    slides = [
        PitchSlide(title="Title", content=[name, description], evidence_status="verified evidence"),
        PitchSlide(title="Problem", content=["This framing comes straight from your own description.", "What's still missing: customer interviews confirming how often this happens and what it costs them."], evidence_status="evidence required"),
        PitchSlide(title="Solution", content=[description], evidence_status="verified evidence"),
        PitchSlide(title="Market", content=[f"I'm reading this as {domain}.", "Unknown: market size — I won't put a number here without a real source behind it."], evidence_status="model inference"),
        PitchSlide(title="Customer", content=[f"Working segment: {segment['segment_name']}." if has_segment else "You haven't confirmed a specific segment yet.", "Validate this before you present it as settled."], evidence_status="deterministic assessment"),
        PitchSlide(title="Product", content=["What's still missing: a demonstrable MVP or prototype outcome to show."], evidence_status="evidence required"),
        PitchSlide(title="Differentiation", content=["What's still missing: a real comparison against the alternatives customers use today."], evidence_status="evidence required"),
        PitchSlide(title="Business Model", content=["Unknown: no pricing or unit-economics evidence has been given yet."], evidence_status="unknown"),
        PitchSlide(title="Traction and evidence", content=["Unknown: no revenue, customers, or partnerships have been confirmed yet.", f"Your next evidence milestone: {next_milestone}."], evidence_status="unknown"),
        PitchSlide(title="Go-to-Market", content=[go_to_market, "What's still missing: real results from actually running that channel."], evidence_status="evidence required" if not channels else "deterministic assessment"),
        PitchSlide(title="Competition", content=["What's still missing: named alternatives and a clear reason customers would switch."], evidence_status="evidence required"),
        PitchSlide(title="Financial Outlook", content=["Unknown: no revenue, cost, pricing, or forecast evidence has been given yet."], evidence_status="unknown"),
        PitchSlide(title="Risks and next milestone", content=["Close your readiness gaps before you make a funding ask.", f"Where you stand today: {funding.get('overall_score', 0)}/100 on my internal readiness read."], evidence_status="deterministic assessment"),
        PitchSlide(title="Team", content=["What's still missing: your team's roles and how they cover the skills this needs."], evidence_status="evidence required"),
        PitchSlide(title="Funding Ask or Next Milestone", content=[f"Your next milestone: {next_milestone}.", "Unknown: no funding ask has been defined yet."], evidence_status="unknown"),
        PitchSlide(title="Closing Vision", content=["Working assumption: this problem can be validated with a focused early-adopter workflow."], evidence_status="assumption"),
        PitchSlide(title="Executive Summary", content=[f"{name}: prove the problem is real with {segment['segment_name'] if has_segment else 'a real first segment'} before claiming traction or market size."], evidence_status="deterministic assessment"),
        PitchSlide(title="Demo Script", content=["Show the target user's current problem, the smallest proposed workflow, and the observable outcome you're trying to validate."], evidence_status="assumption"),
    ]
    return [item.model_dump() for item in slides]
