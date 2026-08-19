"""Business Model Agent (Student 2).

Evaluates the startup against a Business Model Canvas structure using only submitted evidence and
the deterministic outputs already computed upstream (funding-readiness rubric, revenue scenario).
No price, margin, CAC, LTV, revenue, or cost figure is invented — every numeric claim traces back
to either the user's own `revenue_assumptions` or is explicitly marked unknown with a recommended
experiment to fill the gap.
"""

from __future__ import annotations

AGENT_VERSION = "v1-deterministic"


def _first_sentence(description: str) -> str:
    description = (description or "").strip()
    if not description:
        return "unknown"
    for terminator in (". ", "! ", "? "):
        idx = description.find(terminator)
        if idx != -1:
            return description[: idx + 1].strip()
    return description if len(description) <= 200 else description[:200].rsplit(" ", 1)[0] + "..."


def generate_business_model(
    startup_description: str,
    market_evidence: dict,
    revenue_estimate: dict,
    funding_assessment: dict,
) -> dict:
    customer_type = (market_evidence or {}).get("customer_type")
    target_market = (market_evidence or {}).get("target_market")

    breakdown = {item["dimension"]: item for item in funding_assessment.get("breakdown", [])}
    revenue_model_clarity = breakdown.get("revenue_model_clarity", {})
    competitive_differentiation = breakdown.get("competitive_differentiation", {})

    evidence_gaps: list[str] = []
    recommended_experiments: list[str] = []

    value_proposition = _first_sentence(startup_description)
    if value_proposition == "unknown":
        evidence_gaps.append("value_proposition")

    if customer_type or target_market:
        customer_segments = ", ".join(filter(None, [customer_type, target_market])) or "unknown"
    else:
        customer_segments = "unknown"
        evidence_gaps.append("customer_segments")
        recommended_experiments.append("Define and validate the primary customer segment with real interviews.")

    channels = "unknown — you haven't told me how you'll reach customers yet"
    evidence_gaps.append("channels")
    recommended_experiments.append("Test 1-2 candidate acquisition channels and measure conversion.")

    customer_relationships = "unknown — no evidence submitted yet on how you'll support or retain customers"
    evidence_gaps.append("customer_relationships")

    if revenue_estimate and revenue_estimate.get("available"):
        assumptions = revenue_estimate.get("assumptions_used", {})
        price_field = (revenue_estimate.get("assumptions") or {}).get("price_per_customer_usd") or {}
        is_user_supplied = price_field.get("assumption_source") == "user_supplied"
        price_basis = "based on the number you gave me" if is_user_supplied else "a placeholder starting point, not something you've confirmed yet"
        revenue_streams = (
            f"Usage-based pricing at ${assumptions.get('price_per_customer_usd')}/customer/month — "
            f"{price_basis}. See the revenue scenarios below for the full range."
        )
    else:
        revenue_streams = "unknown — you haven't told me your pricing yet"
        evidence_gaps.append("revenue_streams")
        recommended_experiments.append("Define a concrete pricing model and test willingness-to-pay with real prospects.")

    key_resources = "unknown — no evidence submitted yet on what this venture depends on to run"
    key_activities = "unknown — no evidence submitted yet on the core activities this venture performs"
    key_partners = "unknown — no evidence submitted yet on who this venture would need to partner with"
    evidence_gaps.extend(["key_resources", "key_activities", "key_partners"])

    cost_structure = "unknown — no cost data submitted yet"
    evidence_gaps.append("cost_structure")
    recommended_experiments.append("Track your real acquisition and operating costs once you're live.")

    if revenue_model_clarity.get("raw_score") == 2 and revenue_estimate and revenue_estimate.get("available"):
        unit_economics_readiness = "You've defined your pricing and revenue assumptions — that's real groundwork most founders skip."
    elif revenue_model_clarity.get("raw_score") in (0, None):
        unit_economics_readiness = "Your revenue model isn't defined yet — that's the next thing worth nailing down."
        evidence_gaps.append("unit_economics_readiness")
    else:
        unit_economics_readiness = "You've got a partial read on your unit economics — worth sharpening as you go."

    if competitive_differentiation.get("raw_score") == 2:
        scalability = "You already have some real differentiation — how far it scales still depends on channels and costs you haven't validated yet."
    else:
        scalability = "I can't assess scalability yet — there's no differentiation or channel evidence to reason from."

    return {
        "agent_version": AGENT_VERSION,
        "value_proposition": value_proposition,
        "customer_segments": customer_segments,
        "channels": channels,
        "customer_relationships": customer_relationships,
        "revenue_streams": revenue_streams,
        "key_resources": key_resources,
        "key_activities": key_activities,
        "key_partners": key_partners,
        "cost_structure": cost_structure,
        "unit_economics_readiness": unit_economics_readiness,
        "scalability": scalability,
        "evidence_gaps": sorted(set(evidence_gaps)),
        "recommended_experiments": recommended_experiments,
        "source_attribution": {
            "value_proposition": "user-submitted startup_description (first sentence)",
            "revenue_streams": "user-submitted revenue_assumptions via app.ml.revenue_scenario"
            if revenue_estimate and revenue_estimate.get("available")
            else "unavailable — no revenue_assumptions submitted",
            "unit_economics_readiness": "deterministic funding-readiness rubric (revenue_model_clarity dimension)",
        },
        "disclaimer": (
            "I never invent a price, margin, cost, or revenue figure. Anywhere you see \"unknown\" "
            "above, it's because you haven't given me that evidence yet — each one comes with a "
            "concrete way to go find it."
        ),
    }
