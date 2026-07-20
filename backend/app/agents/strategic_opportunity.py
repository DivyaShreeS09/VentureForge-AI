"""Deterministic Strategic Opportunity Discovery baseline (Phase 3).

Answers "where else could this startup realistically succeed, and why?" — strategic reasoning
layered on top of everything the pipeline already computed (venture_positioning,
market_intelligence, customer_personas, business_model, competitor_analysis, feature_gap_analysis,
founder_guidance_items, idea_expansion). No network call, never fabricates a fact about the
specific company.

Produces exactly four sections:
  - `primary_opportunity`: a single item reasoning through why the CURRENT positioning is strong
    (demand, buyer, urgency, willingness to pay, competition, implementation difficulty) — fully
    deterministic; Gemini never touches this (see app.agents.strategic_opportunity_reviewer).
  - `adjacent_opportunities`: markets similar to the current one, each explained through a shared
    workflow/problem/buyer, never a bare list of names.
  - `future_expansion`: five-year-horizon forms this venture could grow into (platform,
    marketplace, developer API, enterprise suite, analytics product, compliance product), each
    reasoned from the venture's own capabilities/deployment breadth, not asserted.
  - `strategic_risks`: market/timing/regulatory/technology/competition/adoption risks — distinct
    from founder execution gaps (see app.agents.founder_guidance) — each with why/likelihood/
    impact/mitigation.

Every item (except risks, which use "risk" as the headline) carries the same
opportunity/reason/evidence/confidence_tier/recommended_next_step shape, plus founder decision
support fields (potential_revenue, difficulty, time_to_market, validation_effort, suitable_stage).
"""

from __future__ import annotations

STRATEGIC_OPPORTUNITY_VERSION = "v1"

_CONFIRMED = "confirmed_from_evidence"
_HYPOTHESIS = "reasonable_hypothesis"
_SPECULATIVE = "speculative_future_opportunity"

# Curated, versioned adjacent-market reasoning per controlled taxonomy primary_domain — mirrors the
# hand-curated, never-invented-per-input approach already used by app.ml.capability_library. Each
# entry explains the SHARED workflow/problem/buyer, never just a market name.
_ADJACENT_REASONING: dict[str, list[tuple[str, str]]] = {
    "Smart Facilities Technology": [
        ("Hospitals", "Hospitals require continuous monitoring of distributed facilities, similar to universities and campuses."),
        ("Hotels", "Hotels manage occupancy, maintenance, and utilities at building scale — the same core workflow this venture already serves."),
        ("Airports", "Airports operate large, always-on facilities with the same utility- and occupancy-monitoring needs, just at greater scale."),
        ("Corporate Campuses", "Corporate campuses face the same multi-building utility and occupancy management problem as a university campus."),
    ],
    "PropTech": [
        ("Hotels", "Hotels manage occupancy, maintenance, and utilities at building scale — the same core workflow this venture already serves."),
        ("Corporate Campuses", "Corporate campuses face the same multi-building management problem as a commercial property portfolio."),
    ],
    "Sustainability Technology": [
        ("Hotels", "Hotels track the same energy, water, and waste metrics for sustainability reporting."),
        ("Government Facilities", "Government facilities face similar carbon-accounting and emissions-reporting requirements at scale."),
        ("Corporate Campuses", "Corporate ESG reporting requires the same underlying sustainability-metric tracking as a campus does."),
    ],
    "Clinical Decision Support": [
        ("Insurance", "Insurers share the same underlying need to assess risk signals from health data for underwriting and claims."),
        ("Telemedicine providers", "Telemedicine platforms already handle remote patient interactions and need the same triage/risk-flagging workflow."),
        ("Clinical Research Organizations", "Clinical research relies on the same structured patient-data review and longitudinal tracking workflow."),
        ("Workplace Wellness Programs", "Workplace wellness programs need the same continuous health-signal monitoring, just for a healthy population."),
    ],
    "Remote Patient Monitoring": [
        ("Insurance", "Insurers share the same underlying need to assess risk signals from patient data for underwriting and claims."),
        ("Telemedicine providers", "Telemedicine platforms already handle remote patient interactions and need the same monitoring workflow."),
        ("Workplace Wellness Programs", "Workplace wellness programs need the same continuous health-signal monitoring, just for a healthy population."),
    ],
    "HealthTech Diagnostics": [
        ("Insurance", "Insurers share the same underlying need to assess risk signals from health data for underwriting and claims."),
        ("Clinical Research Organizations", "Clinical research relies on the same structured, longitudinal review of diagnostic signals."),
        ("Telemedicine providers", "Telemedicine platforms need the same triage/risk-flagging workflow this venture already provides."),
    ],
    "Restaurant Operations Technology": [
        ("Hotels", "Hotel kitchens face the same food-cost and inventory-waste problem restaurants do, just at larger scale."),
        ("Catering companies", "Catering operations share the same perishable-inventory and waste-tracking workflow."),
        ("Grocery/Convenience retail", "Grocery retailers manage the same spoilage and shrink problem for perishable inventory."),
    ],
    "Food-Cost Management": [
        ("Hotels", "Hotel kitchens face the same food-cost and inventory-waste problem restaurants do, just at larger scale."),
        ("Catering companies", "Catering operations share the same perishable-inventory and waste-tracking workflow."),
        ("Grocery/Convenience retail", "Grocery retailers manage the same spoilage and shrink problem for perishable inventory."),
    ],
    "Campus & Student Services": [
        ("Corporate onboarding programs", "Corporate onboarding faces the same need to match new members into groups quickly."),
        ("Professional communities/conferences", "Conferences need the same short-window matching/team-formation workflow as a hackathon."),
    ],
    "Peer Collaboration Marketplaces": [
        ("Corporate onboarding programs", "Corporate onboarding faces the same need to match new members into groups quickly."),
        ("Professional communities/conferences", "Conferences need the same short-window matching/team-formation workflow as a hackathon."),
    ],
    "EdTech": [
        ("Corporate training programs", "Corporate training faces the same structured-curriculum and progress-tracking need as a classroom."),
        ("Professional certification providers", "Certification providers need the same content-delivery and assessment workflow."),
    ],
}

_GENERIC_ADJACENT = [
    (
        "Adjacent teams within the same buyer organization",
        "The same core workflow already solved for one team is usually needed by adjacent teams facing an identical problem, without requiring a new buyer relationship.",
    ),
]

# Five-year-horizon future forms — generic across domains, but the reasoning always references
# this venture's own capabilities/deployment breadth rather than asserting a form is right for it.
def _future_expansion_items(primary_domain: str | None, deployment_sectors: list[str], capability_labels: list[str]) -> list[dict]:
    domain_label = primary_domain or "this space"
    capability_text = ", ".join(capability_labels[:3]) if capability_labels else "its core workflow"
    multi_site_signal = len(deployment_sectors) >= 2

    items = [
        {
            "opportunity": "Platform",
            "reason": (
                f"As more {domain_label} sites adopt this, a platform serving many sites/organizations "
                "at once becomes viable, rather than one deployment per customer."
            ),
            "evidence": (
                f"Already relevant to {len(deployment_sectors)} distinct deployment sectors ({', '.join(deployment_sectors)})."
                if multi_site_signal
                else "No multi-sector deployment signal yet — this is a forward-looking possibility, not a confirmed trend."
            ),
            "confidence_tier": _HYPOTHESIS if multi_site_signal else _SPECULATIVE,
        },
        {
            "opportunity": "Marketplace",
            "reason": (
                "If two distinct sides of this market emerge (e.g. buyers and independent service "
                "providers), a marketplace connecting them could follow the core workflow already proven."
            ),
            "evidence": "No two-sided market signal confirmed yet — a five-year-horizon possibility.",
            "confidence_tier": _SPECULATIVE,
        },
        {
            "opportunity": "Developer API",
            "reason": (
                f"Once {capability_text} is proven, exposing it as an API lets other software integrate "
                "it directly rather than requiring a full standalone product."
            ),
            "evidence": f"Builds on {capability_text}, already part of this venture's capability set.",
            "confidence_tier": _SPECULATIVE,
        },
        {
            "opportunity": "Enterprise Suite",
            "reason": (
                f"Bundling {capability_text} into one suite becomes viable once each capability is "
                "proven individually across more than one deployment."
            ),
            "evidence": "Depends on capabilities beyond what's confirmed present today.",
            "confidence_tier": _SPECULATIVE,
        },
        {
            "opportunity": "Analytics Platform",
            "reason": (
                f"The operational data this product already collects (via {capability_text}) is a "
                "natural foundation for a standalone analytics/reporting product."
            ),
            "evidence": f"Grounded in {capability_text}, already part of this venture's capability set.",
            "confidence_tier": _HYPOTHESIS if capability_labels else _SPECULATIVE,
        },
        {
            "opportunity": "Compliance Platform",
            "reason": (
                f"If {domain_label} adoption pushes into more regulated segments, packaging the "
                "underlying data trail as a compliance/reporting product could follow."
            ),
            "evidence": "No regulatory requirement confirmed yet — a distant, speculative possibility.",
            "confidence_tier": _SPECULATIVE,
        },
    ]
    for item in items:
        item["recommended_next_step"] = "Revisit once the core product has multiple proven deployments — not a near-term build priority."
        item["source"] = "deterministic"
    return items


_RISK_CATEGORIES = ("market", "timing", "regulatory", "technology", "competition", "adoption")

# Domains where a regulatory pathway is a real, well-known consideration (mirrors
# app.ml.capability_library's health capability set, which already models this via
# `regulatory_documentation`/`autonomous_diagnosis` prerequisites).
_REGULATED_DOMAINS = frozenset({"Clinical Decision Support", "Remote Patient Monitoring", "HealthTech Diagnostics"})


def _strategic_risks(
    primary_domain: str | None,
    competitor_analysis: dict | None,
    feature_gap: dict,
    founder_guidance_items: list[dict],
) -> list[dict]:
    risks: list[dict] = []

    # Market risk — always applicable, generically framed, never claims confirmed evidence.
    risks.append({
        "risk": "Market may be narrower than assumed",
        "category": "market",
        "why": f"If adoption for {primary_domain or 'this idea'} stays niche, the addressable market may be smaller than the current positioning assumes.",
        "likelihood": "medium",
        "impact": "medium",
        "mitigation": "Validate demand in a second and third sub-segment before assuming market-wide demand.",
        "confidence_tier": _HYPOTHESIS,
        "source": "deterministic",
    })

    # Timing risk — generic budget-cycle framing.
    risks.append({
        "risk": "Mistimed buyer budget cycle",
        "category": "timing",
        "why": "If the buyer's budget cycle for this category runs annually, a mistimed pitch can stall adoption by a full cycle.",
        "likelihood": "medium",
        "impact": "medium",
        "mitigation": "Learn the target buyer's budgeting calendar during discovery and time outreach accordingly.",
        "confidence_tier": _HYPOTHESIS,
        "source": "deterministic",
    })

    # Regulatory risk — only elevated for known-regulated domains; otherwise flagged low/generic.
    if primary_domain in _REGULATED_DOMAINS:
        risks.append({
            "risk": "Regulatory pathway not yet confirmed",
            "category": "regulatory",
            "why": f"{primary_domain} ventures typically require a defined regulatory pathway before broader deployment.",
            "likelihood": "high",
            "impact": "high",
            "mitigation": "Consult on the applicable regulatory pathway before scaling beyond a clinician-reviewed pilot.",
            "confidence_tier": _CONFIRMED,
            "source": "deterministic",
        })
    else:
        risks.append({
            "risk": "No material regulatory exposure identified yet",
            "category": "regulatory",
            "why": "No regulatory pathway is currently required for this domain, but this can change if the venture expands into a regulated sector.",
            "likelihood": "low",
            "impact": "low",
            "mitigation": "Revisit if entering a new, regulated deployment sector (e.g. healthcare, finance, government).",
            "confidence_tier": _HYPOTHESIS,
            "source": "deterministic",
        })

    # Technology risk — from feature_gap's premature capabilities (unbuilt prerequisites).
    premature = feature_gap.get("premature_capabilities", [])
    if premature:
        labels = ", ".join(c["label"] for c in premature[:3])
        risks.append({
            "risk": "Advanced capabilities depend on unbuilt infrastructure",
            "category": "technology",
            "why": f"{labels} depend on prerequisites not yet built — a roadmap that assumes them too early carries technical risk.",
            "likelihood": "medium",
            "impact": "medium",
            "mitigation": "Sequence the roadmap so each capability's prerequisites are proven before building it.",
            "confidence_tier": _CONFIRMED,
            "source": "deterministic",
        })

    # Competition risk — from competitor_analysis.
    verified = (competitor_analysis or {}).get("verified_competitors") or []
    if verified:
        names = ", ".join(c["name"] for c in verified[:3])
        risks.append({
            "risk": "Named alternatives already exist",
            "category": "competition",
            "why": f"The founder already named real alternatives ({names}) — differentiation must be concrete, not assumed.",
            "likelihood": "high",
            "impact": "medium",
            "mitigation": "Confirm a specific, defensible differentiation against each named alternative before scaling spend.",
            "confidence_tier": _CONFIRMED,
            "source": "deterministic",
        })
    else:
        risks.append({
            "risk": "Category-level alternatives remain the real competition",
            "category": "competition",
            "why": "No verified named competitor yet, but manual processes and 'doing nothing' are still real alternatives a buyer will compare against.",
            "likelihood": "medium",
            "impact": "medium",
            "mitigation": "Validate willingness to switch away from the manual/status-quo alternative, not just interest in the product.",
            "confidence_tier": _HYPOTHESIS,
            "source": "deterministic",
        })

    # Adoption risk — from founder_guidance validation/discovery items on traction/customer pain.
    adoption_gap = next(
        (item for item in founder_guidance_items if item["dimension"] in ("traction", "customer_pain_evidence") and item["category"] in ("validation_opportunity", "discovery_question", "confirmed_risk")),
        None,
    )
    if adoption_gap:
        risks.append({
            "risk": "Adoption not yet confirmed",
            "category": "adoption",
            "why": f"{adoption_gap['title']} — until a real pilot validates demand, adoption risk remains open.",
            "likelihood": "medium",
            "impact": "high",
            "mitigation": adoption_gap["next_step"],
            "confidence_tier": _HYPOTHESIS,
            "source": "deterministic",
        })

    return risks


def _build_primary_opportunity(
    venture_positioning: dict,
    market_intelligence: dict | None,
    customer_personas: dict | None,
    business_model: dict | None,
    competitor_analysis: dict | None,
    feature_gap: dict,
    founder_guidance_items: list[dict],
    funding_assessment: dict,
) -> dict:
    primary_domain = venture_positioning.get("primary_domain") or "the current positioning"

    demand = (
        (market_intelligence or {}).get("market_summary")
        or "Not yet established — no market intelligence evidence submitted."
    )
    personas = (customer_personas or {}).get("personas") or []
    buyer = personas[0]["role_or_context"] if personas else "Not yet named by the founder."

    traction_item = next((i for i in founder_guidance_items if i["dimension"] == "traction"), None)
    urgency = (
        "Demonstrated — traction evidence already confirmed."
        if traction_item and traction_item["category"] == "strength"
        else "Not yet confirmed — no traction evidence submitted."
    )

    revenue_streams = (business_model or {}).get("revenue_streams")
    willingness_to_pay = (
        revenue_streams if revenue_streams and "unknown" not in revenue_streams.lower()
        else "Not yet confirmed — no revenue-model evidence submitted."
    )

    verified_competitors = (competitor_analysis or {}).get("verified_competitors") or []
    competition = (
        f"Named alternatives exist: {', '.join(c['name'] for c in verified_competitors[:3])}."
        if verified_competitors
        else "No verified named competitor yet — category-level alternatives only."
    )

    premature_count = len(feature_gap.get("premature_capabilities", []))
    present_count = len(feature_gap.get("present_capabilities", []))
    if present_count and not premature_count:
        implementation_difficulty = "low"
    elif premature_count <= 1:
        implementation_difficulty = "medium"
    else:
        implementation_difficulty = "high"

    confirmed_signals = sum([
        bool(market_intelligence),
        bool(personas),
        bool(traction_item and traction_item["category"] == "strength"),
    ])
    confidence_tier = _CONFIRMED if confirmed_signals >= 2 else _HYPOTHESIS

    level = funding_assessment.get("level", "early_stage")
    suitable_stage = {"ready": "growth", "developing": "pilot", "early_stage": "prototype"}.get(level, "idea")

    top_actionable = next(
        (i for i in founder_guidance_items if i["category"] in ("confirmed_risk", "validation_opportunity", "discovery_question")),
        None,
    )
    recommended_next_step = top_actionable["next_step"] if top_actionable else "Continue validating demand with a concrete pilot commitment."

    return {
        "opportunity": primary_domain,
        "reason": (
            f"{primary_domain} is the strongest current positioning because it is where this venture's "
            "own evidence — market signal, named buyer, and capability fit — already concentrates."
        ),
        "evidence": (
            f"Demand: {demand} Buyer: {buyer} Urgency: {urgency} Willingness to pay: {willingness_to_pay} "
            f"Competition: {competition}"
        ),
        "confidence_tier": confidence_tier,
        "recommended_next_step": recommended_next_step,
        "potential_revenue": "Not yet quantified — see Revenue Estimate for scenario ranges." if not revenue_streams else revenue_streams,
        "difficulty": implementation_difficulty,
        "time_to_market": {"low": "1-3 months", "medium": "3-6 months", "high": "6-12+ months"}[implementation_difficulty],
        "validation_effort": "One concrete pilot commitment" if suitable_stage in ("idea", "prototype") else "Ongoing measurement across existing pilots",
        "suitable_stage": suitable_stage,
        "source": "deterministic",
        "demand": demand,
        "buyer": buyer,
        "urgency": urgency,
        "willingness_to_pay": willingness_to_pay,
        "competition": competition,
        "implementation_difficulty": implementation_difficulty,
    }


def _adjacent_opportunity_items(primary_domain: str | None) -> list[dict]:
    candidates = _ADJACENT_REASONING.get(primary_domain or "", _GENERIC_ADJACENT)
    items = []
    for market, reason in candidates:
        items.append({
            "opportunity": market,
            "reason": reason,
            "evidence": f"Derived from this venture's own positioning ({primary_domain}) and its known shared-workflow reasoning.",
            "confidence_tier": _HYPOTHESIS,
            "recommended_next_step": f"Interview one potential buyer in {market} to confirm the shared problem actually holds.",
            "potential_revenue": "Not yet quantified — a new segment requires its own validation before estimating revenue.",
            "difficulty": "medium",
            "time_to_market": "3-6 months",
            "validation_effort": "1-2 discovery interviews in the adjacent segment",
            "suitable_stage": "pilot",
            "source": "deterministic",
        })
    return items


def build_deterministic_strategic_opportunity(
    venture_positioning: dict,
    market_intelligence: dict | None,
    customer_personas: dict | None,
    business_model: dict | None,
    competitor_analysis: dict | None,
    feature_gap: dict,
    founder_guidance_items: list[dict],
    funding_assessment: dict,
) -> dict:
    """Build the complete, always-available Strategic Opportunity Discovery baseline. Fully
    deterministic, no network call. Never changes venture_positioning, funding_assessment,
    mentor_verdict, classifier output, historical pattern signal, customer_personas, judge output,
    or idea_expansion — those remain authoritative and untouched (see
    app.agents.strategic_opportunity_reviewer for the optional additive Gemini layer on top).
    """
    primary_domain = venture_positioning.get("primary_domain")
    deployment_sectors = venture_positioning.get("deployment_sectors") or []
    present_capability_labels = [c["label"] for c in feature_gap.get("present_capabilities", [])]

    return {
        "strategic_opportunity_version": STRATEGIC_OPPORTUNITY_VERSION,
        "source": "deterministic",
        "primary_opportunity": _build_primary_opportunity(
            venture_positioning, market_intelligence, customer_personas, business_model,
            competitor_analysis, feature_gap, founder_guidance_items, funding_assessment,
        ),
        "adjacent_opportunities": _adjacent_opportunity_items(primary_domain),
        "future_expansion": _future_expansion_items(primary_domain, deployment_sectors, present_capability_labels),
        "strategic_risks": _strategic_risks(primary_domain, competitor_analysis, feature_gap, founder_guidance_items),
    }
