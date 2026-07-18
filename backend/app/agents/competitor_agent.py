"""Competitor Analysis Agent (Student 2).

Never invents a real company, its pricing, market share, funding, or customer count — no
competitor database or web-search integration exists in this system, so any named-company detail
beyond what the user themselves typed would be fabrication. When the user supplies competitor
names (`market_evidence.known_competitors`), each is echoed back with every analytical field
explicitly marked unknown/requires-research (the system has no way to verify or research a named
company). When no names are supplied, the agent falls back to *category-level* alternatives
(generic, explicitly labeled as categories, never presented as named verified companies).
"""

from __future__ import annotations

AGENT_VERSION = "v1-deterministic"

_GENERIC_ALTERNATIVE_CATEGORIES = [
    "Other {industry} tools/products serving a similar customer",
    "Manual or spreadsheet-based process (status quo alternative)",
    "Doing nothing / no solution adopted",
]


def generate_competitor_analysis(
    known_competitors: list[str],
    industry_prediction: dict | None,
) -> dict:
    industry_label = (industry_prediction or {}).get("predicted_industry") or "this"
    entries: list[dict] = []

    if known_competitors:
        for name in known_competitors:
            entries.append(
                {
                    "competitor_or_alternative": name,
                    "category": "user-named competitor (not independently verified)",
                    "comparable_capability": "unknown — no verified product/feature data available",
                    "likely_strength": "unknown — requires independent research",
                    "likely_weakness": "unknown — requires independent research",
                    "differentiation_gap": "unknown — requires direct comparison research",
                    "evidence_source": "user-submitted (market_evidence.known_competitors)",
                    "confidence": "low",
                    "unknown_fields": [
                        "category",
                        "comparable_capability",
                        "likely_strength",
                        "likely_weakness",
                        "differentiation_gap",
                    ],
                }
            )
        recommended_action = (
            "Independently research each named competitor's actual product, pricing, and "
            "positioning — this system does not verify or fetch third-party company data."
        )
    else:
        for template in _GENERIC_ALTERNATIVE_CATEGORIES:
            entries.append(
                {
                    "competitor_or_alternative": template.format(industry=industry_label),
                    "category": "generic alternative category (no named companies)",
                    "comparable_capability": "unknown — category-level only, no specific product identified",
                    "likely_strength": "unknown",
                    "likely_weakness": "unknown",
                    "differentiation_gap": "unknown — requires identifying and researching real named alternatives",
                    "evidence_source": "derived category (no user-submitted competitor names)",
                    "confidence": "low",
                    "unknown_fields": [
                        "comparable_capability",
                        "likely_strength",
                        "likely_weakness",
                        "differentiation_gap",
                    ],
                }
            )
        recommended_action = "Identify and name 2-3 real, specific alternatives customers currently use."

    return {
        "agent_version": AGENT_VERSION,
        "entries": entries,
        "recommended_validation_actions": [recommended_action],
        "disclaimer": (
            "No competitor database or web-search integration exists in this system. Real company "
            "names, pricing, market share, funding, or customer counts are never fabricated here — "
            "only what the user directly submitted is echoed back, or generic unverified categories "
            "are suggested when no competitor names were given."
        ),
    }
