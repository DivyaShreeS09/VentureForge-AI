"""Deterministic Idea Expansion baseline (Phase 2).

Generates the always-available fallback for the founder-facing "Idea Expansion" capability —
alternative customer segments, adjacent industries, feature ideas, pricing models, MVP
simplification, pivot opportunities, partnerships, and go-to-market ideas — entirely from data
this venture's own pipeline already computed (venture_positioning, feature_gap_analysis,
mvp_recommendation). No network call, never fabricates a fact about the specific company.

Every item carries a `confidence_tier`:
  - "confirmed_from_evidence": derived directly from this venture's own already-computed
    deterministic data (its taxonomy match, its capability classification). This tier is reserved
    for this module only — see app.agents.idea_expansion_reviewer, whose Gemini-authored items can
    never claim it (the Gemini schema has no such enum value).
  - "reasonable_hypothesis": a well-known general business pattern applied to this venture's
    domain, not asserted as a fact about the company itself (e.g. generic pricing-model tradeoffs,
    generic partnership categories).

Never presents a Tier-2 hypothesis as settled fact, and never recommends a pivot outright — pivot
items are always framed as "if X is slow, Y may also fit," never "you should pivot" (see
`_pivot_opportunities`).
"""

from __future__ import annotations

IDEA_EXPANSION_VERSION = "v1"

_CONFIRMED = "confirmed_from_evidence"
_HYPOTHESIS = "reasonable_hypothesis"

# Generic, domain-agnostic monetization patterns — well-established business knowledge, not a
# claim about this specific company. Always `reasonable_hypothesis`: every venture could in
# principle try any of these, but none is confirmed as right for this one.
_PRICING_MODELS = [
    {
        "title": "Subscription (flat recurring fee)",
        "reason": "Predictable recurring revenue and easy to forecast; best once the core workflow "
        "is proven and used repeatedly, not for a one-time or occasional-use product.",
    },
    {
        "title": "Freemium (free tier + paid upgrade)",
        "reason": "Lowers the barrier to first use and can build a user base quickly, but requires a "
        "clear, compelling reason to upgrade — risky before that upgrade trigger is validated.",
    },
    {
        "title": "Usage-based pricing",
        "reason": "Aligns price with the value actually delivered and feels fair to early, "
        "low-volume users, but makes revenue harder to forecast until usage patterns stabilize.",
    },
    {
        "title": "Enterprise licensing",
        "reason": "Can capture large per-deal revenue from bigger organizations, but usually requires "
        "a longer sales cycle and more proven credibility than an early-stage venture may have yet.",
    },
    {
        "title": "Marketplace / transaction fee",
        "reason": "Only earns revenue when a real transaction happens between two sides, so it scales "
        "naturally with usage — but requires enough two-sided volume to be worthwhile.",
    },
]

# Generic go-to-market moves, framed around whatever this venture's own MVP/pilot plan already
# established — not a claim about the company's actual traction.
_GENERIC_GTM_STEPS = [
    "Secure one concrete pilot site or customer before any broader launch.",
    "Ask the pilot's early users for a testimonial or referral once value is demonstrated.",
    "Publish the pilot's results as a short case study once there's a real outcome to report.",
]

# Generic partnership categories, loosely keyed by deployment sector — realistic categories of
# organization, not a claim that any specific one has agreed to anything.
_PARTNERSHIP_CATEGORIES_BY_SECTOR: dict[str, list[dict]] = {
    "Universities": [{"title": "University IT or facilities departments", "reason": "Often the budget holder and first adopter for campus-facing tools in this space."}],
    "Campuses": [{"title": "Campus operations or student-life offices", "reason": "Frequently own the budget and rollout process for campus-wide pilots."}],
    "Hospitals": [{"title": "Hospital IT and procurement teams", "reason": "Typically the gatekeeper for any tool touching clinical or facility workflows."}],
    "Clinics": [{"title": "Independent clinic networks", "reason": "Smaller and faster to pilot with than a full hospital system."}],
    "Hotels": [{"title": "Hospitality management groups", "reason": "Often manage several properties, making one relationship a path to several pilot sites."}],
    "Restaurants": [{"title": "Point-of-sale (POS) vendors", "reason": "A natural integration partner if the product already touches inventory or sales data."}],
    "Consumer Households": [{"title": "Consumer app distribution communities", "reason": "A low-cost channel to reach early individual users directly."}],
}
_GENERIC_PARTNERSHIPS = [
    {"title": "Cloud infrastructure providers (e.g. AWS, Google Cloud, Microsoft Azure)", "reason": "Startup credit programs can meaningfully extend runway at this stage."},
    {"title": "Payment providers", "reason": "Relevant once a paid pricing model (see pricing_models) is being tested."},
]


def _confirmed_item(title: str, reason: str) -> dict:
    return {"title": title, "reason": reason, "confidence_tier": _CONFIRMED, "source": "deterministic"}


def _hypothesis_item(title: str, reason: str) -> dict:
    return {"title": title, "reason": reason, "confidence_tier": _HYPOTHESIS, "source": "deterministic"}


def _customer_segments(deployment_sectors: list[str], current_target_user: str | None) -> list[dict]:
    return [
        _confirmed_item(
            sector,
            f"Already identified as a deployment sector for ventures in this space — the "
            f"underlying capability likely transfers, even if {current_target_user or 'the current target user'} "
            "remains the first segment to validate.",
        )
        for sector in deployment_sectors
    ]


def _adjacent_industries(primary_domain: str | None, secondary_domains: list[str]) -> list[dict]:
    if not primary_domain:
        return []
    return [
        _confirmed_item(
            domain,
            f"Already identified as a secondary domain sharing overlapping needs with "
            f"{primary_domain} in this venture's own positioning.",
        )
        for domain in secondary_domains
    ]


def _feature_ideas(feature_gap: dict) -> list[dict]:
    items = [
        _hypothesis_item(f"Build: {cap['label']}", cap["reason"])
        for cap in feature_gap.get("recommended_capabilities", [])
    ]
    items.extend(
        {
            "title": f"Later: {cap['label']}",
            "reason": cap["reason"],
            "confidence_tier": "speculative_future_opportunity",
            "source": "deterministic",
        }
        for cap in feature_gap.get("premature_capabilities", [])
    )
    return items


def _pivot_opportunities(primary_domain: str | None, secondary_domains: list[str], deployment_sectors: list[str]) -> list[dict]:
    if not primary_domain:
        return []
    candidates = secondary_domains or deployment_sectors
    return [
        _hypothesis_item(
            candidate,
            f"If adoption in {primary_domain} is slower than expected, {candidate} may also fit — "
            "not a suggestion to abandon the current direction, just a related space worth knowing "
            "about.",
        )
        for candidate in candidates
    ]


def _partnerships(deployment_sectors: list[str]) -> list[dict]:
    items: list[dict] = []
    for sector in deployment_sectors:
        for cat in _PARTNERSHIP_CATEGORIES_BY_SECTOR.get(sector, []):
            items.append(_hypothesis_item(cat["title"], cat["reason"]))
    items.extend(_hypothesis_item(p["title"], p["reason"]) for p in _GENERIC_PARTNERSHIPS)
    return items


def _go_to_market(mvp_recommendation: dict, primary_domain: str | None) -> list[dict]:
    steps = list(_GENERIC_GTM_STEPS)
    if primary_domain:
        steps.append(f"Look for communities or directories relevant to {primary_domain} to list the pilot in.")
    return [_hypothesis_item(step, f"A standard early go-to-market step given the pilot plan: {mvp_recommendation.get('pilot_environment', 'one real site, not a broad launch')}.") for step in steps]


def _mvp_simplification(feature_gap: dict, mvp_recommendation: dict) -> dict:
    all_capability_labels = [
        c["label"]
        for c in feature_gap.get("present_capabilities", [])
        + feature_gap.get("recommended_capabilities", [])
        + feature_gap.get("premature_capabilities", [])
    ]
    recommended_labels = [c["label"] for c in feature_gap.get("recommended_capabilities", [])]
    premature_labels = [c["label"] for c in feature_gap.get("premature_capabilities", [])]

    return {
        "current_vision": (
            f"Everything described so far: {', '.join(all_capability_labels)}."
            if all_capability_labels
            else "The full vision as described, before any capability has been scoped down."
        ),
        "simplest_mvp": mvp_recommendation.get("minimum_workflow", "Not yet defined."),
        "version_2": (
            f"Add: {', '.join(recommended_labels[:2])}." if recommended_labels else "No further capability recommended yet — validate the MVP first."
        ),
        "version_3": (
            f"Add: {', '.join(premature_labels[:2])}." if premature_labels else "No advanced capability identified yet."
        ),
        "confidence_tier": _CONFIRMED,
    }


def build_deterministic_idea_expansion(
    venture_positioning: dict,
    feature_gap: dict,
    mvp_recommendation: dict,
    market_evidence: dict | None = None,
) -> dict:
    """Build the complete, always-available Idea Expansion baseline. Fully deterministic, no
    network call — every field populated whether or not Gemini is ever configured (see
    app.agents.idea_expansion_reviewer for the optional additive Gemini layer on top)."""
    market_evidence = market_evidence or {}
    primary_domain = venture_positioning.get("primary_domain")
    secondary_domains = venture_positioning.get("secondary_domains") or []
    deployment_sectors = venture_positioning.get("deployment_sectors") or []
    current_target_user = market_evidence.get("customer_type")

    return {
        "idea_expansion_version": IDEA_EXPANSION_VERSION,
        "source": "deterministic",
        "customer_segments": _customer_segments(deployment_sectors, current_target_user),
        "adjacent_industries": _adjacent_industries(primary_domain, secondary_domains),
        "feature_ideas": _feature_ideas(feature_gap),
        "pricing_models": [_hypothesis_item(p["title"], p["reason"]) for p in _PRICING_MODELS],
        "mvp_simplification": _mvp_simplification(feature_gap, mvp_recommendation),
        "pivot_opportunities": _pivot_opportunities(primary_domain, secondary_domains, deployment_sectors),
        "partnerships": _partnerships(deployment_sectors),
        "go_to_market": _go_to_market(mvp_recommendation, primary_domain),
    }
