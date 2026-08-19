"""Controlled capability library (Full Mentor Orchestration phase).

Keyed by `venture_positioning.primary_domain` (see app.ml.positioning_taxonomy), this is a
hand-curated, versioned list of product capabilities a venture in that domain might build —
never inferred from a model, never invented per-input. Each capability's `matching_concepts` are
plain substrings checked against the startup description (the same deterministic, no-network
approach as app.ml.positioning_taxonomy's keyword matcher) to decide whether it already appears to
be "present" in what the founder described.

Classification (see `classify_capabilities`) sorts every capability in a domain's library into
exactly one of four buckets:
  - present: at least one matching concept found in the description.
  - recommended: not present, but every prerequisite capability IS present (or has no
    prerequisites) — i.e. actually buildable next. Capped at 3-5 high-value items, ranked by
    importance (core > useful > advanced); capped further to at most 1 when the venture
    positioning signal itself is low-confidence (a broad/vague idea should be pointed at user and
    problem discovery, not handed a feature list).
  - premature: not present, and at least one prerequisite capability is NOT present — recommending
    these would skip a dependency (e.g. autonomous diagnosis before a clinician-review workflow
    exists).
  - not_relevant: eligible (prerequisites satisfied) but not selected among the top recommended
    items for this pass — still relevant to the domain, just not among the highest-value next
    steps right now.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CAPABILITY_LIBRARY_VERSION = "v1"

_IMPORTANCE_RANK = {"core": 0, "useful": 1, "advanced": 2}


@dataclass(frozen=True)
class Capability:
    id: str
    label: str
    description: str
    importance: str  # "core" | "useful" | "advanced"
    matching_concepts: tuple[str, ...]
    prerequisites: tuple[str, ...] = field(default_factory=tuple)
    validation_question: str = ""


def _cap(id_: str, label: str, description: str, importance: str, concepts, prereqs=(), question: str = "") -> Capability:
    return Capability(
        id=id_, label=label, description=description, importance=importance,
        matching_concepts=tuple(concepts), prerequisites=tuple(prereqs),
        validation_question=question or f"Is '{label}' actually needed yet, or premature for this stage?",
    )


_FACILITIES_CAPABILITIES = [
    _cap(
        "real_time_utility_monitoring", "Real-Time Utility Monitoring",
        "Live tracking of one or more utilities (electricity, water, occupancy) for a single site.",
        "core", ["monitor", "real time", "occupancy", "electricity", "water", "utility", "utilities"],
        question="Does live monitoring of at least one utility already work for one site?",
    ),
    _cap(
        "multi_building_dashboard", "Multi-Building Dashboard",
        "A single dashboard aggregating monitoring data across more than one building/site.",
        "useful", ["dashboard", "portfolio", "multiple buildings", "multi-site"],
        prereqs=["real_time_utility_monitoring"],
        question="Has real-time monitoring been proven on at least one site first?",
    ),
    _cap(
        "anomaly_alerting", "Anomaly Alerting",
        "Automatic alerts when usage patterns deviate from a normal baseline.",
        "useful", ["alert", "anomaly", "notify", "flags waste"],
        prereqs=["real_time_utility_monitoring"],
        question="Is there enough baseline monitoring data yet to define 'normal' usage?",
    ),
    _cap(
        "predictive_maintenance", "Predictive Maintenance",
        "Forecasting equipment failure before it happens, based on historical sensor trends.",
        "advanced", ["predictive maintenance", "forecast failure"],
        prereqs=["anomaly_alerting"],
        question="Does anomaly alerting already work reliably before predicting failures from it?",
    ),
    _cap(
        "automated_hvac_control", "Automated Facility Control",
        "Automatically adjusting facility systems (HVAC, lighting) rather than only alerting a human.",
        "advanced", ["automated control", "automate hvac", "automatic adjustment"],
        prereqs=["anomaly_alerting"],
        question="Has a human been reliably acting on alerts before automating the response?",
    ),
]

_HEALTH_CAPABILITIES = [
    _cap(
        "risk_flagging", "Risk Flagging",
        "Flags an elevated risk signal for a clinician to review — not an autonomous diagnosis.",
        "core", ["risk", "detection", "screening", "flag"],
        question="Does the risk-flagging logic already work on any real or retrospective data?",
    ),
    _cap(
        "clinician_review_workflow", "Clinician Review Workflow",
        "A structured workflow for a clinician to review and confirm/reject each flagged case.",
        "core", ["clinician", "review", "clinical decision"],
        question="Is there a defined process for a clinician to review flagged cases yet?",
    ),
    _cap(
        "patient_history_tracking", "Patient History Tracking",
        "Longitudinal tracking of a patient's risk signal over multiple visits/readings.",
        "useful", ["history", "longitudinal", "tracking over time"],
        prereqs=["risk_flagging"],
        question="Does single-point risk flagging work before tracking it over time?",
    ),
    _cap(
        "regulatory_documentation", "Regulatory Documentation Pathway",
        "Documentation and classification work needed for the applicable regulatory pathway.",
        "useful", ["regulatory", "compliance", "classification"],
        question="Has a regulatory consultation happened yet to know which pathway applies?",
    ),
    _cap(
        "autonomous_diagnosis", "Autonomous Diagnosis",
        "Making a diagnosis without a clinician in the loop — a materially stricter regulatory class.",
        "advanced", ["autonomous diagnosis", "automatic diagnosis"],
        prereqs=["clinician_review_workflow", "regulatory_documentation"],
        question="Does a clinician-reviewed workflow and a confirmed regulatory pathway exist yet?",
    ),
]

_RESTAURANT_CAPABILITIES = [
    _cap(
        "manual_inventory_logging", "Manual Inventory Logging",
        "Founder or staff manually logs inventory counts (no POS integration required).",
        "core", ["inventory", "track inventory", "count"],
        question="Does manual entry already capture real inventory counts for one location?",
    ),
    _cap(
        "waste_tracking", "Food Waste Tracking",
        "Recording what and how much is thrown away, to quantify the waste-reduction thesis.",
        "core", ["waste", "spoilage", "food waste"],
        question="Is there a real waste-cost baseline being measured yet, even manually?",
    ),
    _cap(
        "pos_integration", "POS Integration",
        "Automatic inventory sync with the restaurant's existing point-of-sale system.",
        "useful", ["pos", "point of sale", "integration"],
        prereqs=["manual_inventory_logging"],
        question="Has the manual-entry version already proven the core value with one restaurant?",
    ),
    _cap(
        "automated_reorder_suggestions", "Automated Reorder Suggestions",
        "Suggesting what to reorder and when, based on historical usage patterns.",
        "advanced", ["automated reorder", "reorder suggestion"],
        prereqs=["pos_integration"],
        question="Is POS-synced inventory data already flowing before automating reorder logic?",
    ),
    _cap(
        "multi_location_reporting", "Multi-Location Reporting",
        "Aggregated reporting across more than one restaurant location.",
        "advanced", ["multi-location", "multiple restaurants", "chain reporting"],
        prereqs=["pos_integration"],
        question="Has POS integration been proven at one location before reporting across many?",
    ),
]

_MARKETPLACE_CAPABILITIES = [
    _cap(
        "profile_and_skill_matching", "Profile & Skill Matching",
        "Basic profile creation and matching people by skill/availability/project type.",
        "core", ["match", "teammate", "skill", "collaboration"],
        question="Does basic matching already work for a real group of people?",
    ),
    _cap(
        "single_event_pilot_mode", "Single-Event Pilot Mode",
        "Running the matching tool scoped to one specific event or campus, not a broad launch.",
        "core", ["hackathon", "event", "campus life", "one campus"],
        question="Has matching been tested inside one bounded event/campus yet?",
    ),
    _cap(
        "messaging", "In-App Messaging",
        "Direct messaging between matched users without leaving the platform.",
        "useful", ["messaging", "chat", "direct message"],
        prereqs=["profile_and_skill_matching"],
        question="Does matching already produce real connections worth messaging about?",
    ),
    _cap(
        "organizer_analytics_dashboard", "Organizer Analytics Dashboard",
        "Analytics for event/campus organizers about match volume and outcomes.",
        "useful", ["organizer", "analytics dashboard"],
        prereqs=["profile_and_skill_matching"],
        question="Is there enough real match volume yet to make organizer analytics meaningful?",
    ),
    _cap(
        "payments_and_monetization", "Payments & Monetization",
        "Charging organizers or users — a monetization layer on top of the core matching value.",
        "advanced", ["payment", "monetiz", "paid tier"],
        prereqs=["profile_and_skill_matching", "organizer_analytics_dashboard"],
        question="Has the core matching value been validated before asking anyone to pay for it?",
    ),
]

_CONSUMER_CAPABILITIES = [
    _cap(
        "core_workflow_prototype", "Core Workflow Prototype",
        "A working version of the single core workflow this idea is built around.",
        "core", ["app", "tool", "workflow", "productivity", "task"],
        question="Does the single core workflow already work for one real user?",
    ),
    _cap(
        "user_feedback_collection", "User Feedback Collection",
        "A lightweight mechanism to collect direct feedback from early users.",
        "core", ["feedback", "survey"],
        question="Is there a channel to hear directly from real users yet?",
    ),
    _cap(
        "basic_usage_tracking", "Basic Usage Tracking",
        "Simple analytics on how the core workflow is actually being used.",
        "useful", ["analytics", "usage tracking", "metrics"],
        prereqs=["core_workflow_prototype"],
        question="Does the core workflow exist yet to have usage worth tracking?",
    ),
    _cap(
        "payment_processing", "Payment Processing",
        "Charging users money for the product.",
        "advanced", ["payment", "subscription", "billing"],
        prereqs=["core_workflow_prototype", "user_feedback_collection"],
        question="Has real user feedback validated the core workflow before monetizing it?",
    ),
]

GENERIC_CAPABILITIES = _CONSUMER_CAPABILITIES

_CAPABILITY_LIBRARY: dict[str, list[Capability]] = {
    "Smart Facilities Technology": _FACILITIES_CAPABILITIES,
    "PropTech": _FACILITIES_CAPABILITIES,
    "Sustainability Technology": _FACILITIES_CAPABILITIES,
    "Enterprise AI": _CONSUMER_CAPABILITIES,
    "Clinical Decision Support": _HEALTH_CAPABILITIES,
    "Remote Patient Monitoring": _HEALTH_CAPABILITIES,
    "HealthTech Diagnostics": _HEALTH_CAPABILITIES,
    "Campus & Student Services": _MARKETPLACE_CAPABILITIES,
    "Peer Collaboration Marketplaces": _MARKETPLACE_CAPABILITIES,
    "EdTech": _MARKETPLACE_CAPABILITIES,
    "Restaurant Operations Technology": _RESTAURANT_CAPABILITIES,
    "Food-Cost Management": _RESTAURANT_CAPABILITIES,
    "Productivity Software": _CONSUMER_CAPABILITIES,
    "General Consumer App": _CONSUMER_CAPABILITIES,
}


def get_capabilities_for_domain(primary_domain: str | None) -> list[Capability]:
    """Every controlled domain in app.ml.positioning_taxonomy.POSITIONING_TAXONOMY has an entry
    above; any other/unknown domain (or None) falls back to `GENERIC_CAPABILITIES` — the
    deterministic fallback always supports every controlled domain, never raises or returns
    nothing."""
    return _CAPABILITY_LIBRARY.get(primary_domain or "", GENERIC_CAPABILITIES)


def _capability_dict(cap: Capability, reason: str) -> dict:
    return {
        "id": cap.id,
        "label": cap.label,
        "description": cap.description,
        "importance": cap.importance,
        "prerequisites": list(cap.prerequisites),
        "validation_question": cap.validation_question,
        "reason": reason,
    }


def classify_capabilities(description: str, primary_domain: str | None, is_low_confidence: bool) -> dict:
    """Returns `{present_capabilities, recommended_capabilities, premature_capabilities,
    not_relevant_capabilities}`, each a list of capability dicts (see `_capability_dict`).
    """
    capabilities = get_capabilities_for_domain(primary_domain)
    text_norm = description.lower()

    present: list[Capability] = []
    present_ids: set[str] = set()
    for cap in capabilities:
        matched = [c for c in cap.matching_concepts if c in text_norm]
        if matched:
            present.append(cap)
            present_ids.add(cap.id)

    remaining = [c for c in capabilities if c.id not in present_ids]
    eligible = [c for c in remaining if set(c.prerequisites).issubset(present_ids)]
    premature = [c for c in remaining if not set(c.prerequisites).issubset(present_ids)]

    eligible_sorted = sorted(eligible, key=lambda c: (_IMPORTANCE_RANK[c.importance], c.id))

    # A low-confidence / vague venture positioning must stay focused on discovery, not feature
    # inflation — cap recommendations hard, favoring at most one core discovery-adjacent item.
    if is_low_confidence:
        core_only = [c for c in eligible_sorted if c.importance == "core"]
        max_recommended = 1 if core_only else 0
        recommended = core_only[:max_recommended]
    else:
        recommended = eligible_sorted[:5]
        if len(recommended) < 3:
            recommended = eligible_sorted[: min(3, len(eligible_sorted))]

    recommended_ids = {c.id for c in recommended}
    not_relevant = [c for c in eligible_sorted if c.id not in recommended_ids]

    return {
        "present_capabilities": [
            _capability_dict(c, f"Matched in the founder's description: {', '.join(w for w in c.matching_concepts if w in text_norm)}.")
            for c in present
        ],
        "recommended_capabilities": [
            _capability_dict(c, "A strong next capability to build — everything it depends on is already in place.")
            for c in recommended
        ],
        "premature_capabilities": [
            _capability_dict(
                c,
                f"A great next step once {', '.join(c.prerequisites)} "
                f"{'is' if len(c.prerequisites) == 1 else 'are'} in place — for now, focus on what's already working.",
            )
            for c in premature
        ],
        "not_relevant_capabilities": [
            _capability_dict(c, "Eligible but not among the highest-value next steps for this pass.")
            for c in not_relevant
        ],
    }
