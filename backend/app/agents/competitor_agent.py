"""Competitor Analysis Agent (Student 2, restructured into 5 explicit buckets for Phase B).

Never invents a real company, its pricing, market share, funding, or customer count — no
competitor database or web-search integration exists in this system, so any named-company detail
beyond what the user themselves typed would be fabrication.

Five explicit buckets (see the approved architecture plan §6), each independently attributed:

  - `verified_competitors`: only ever from literal user-submitted names (market_evidence.
    known_competitors) — still labeled `unverified_by_system` per company, since this system has
    no way to verify or research a named company on its own.
  - `unverified_possibilities`: Gemini-suggested *category-level* possibilities only, schema-
    sanitized to never assert a specific proper-noun company the user didn't supply. Empty when
    Gemini is unavailable or unconfigured — the deterministic fallback never invents companies to
    fill this bucket.
  - `indirect_alternatives`, `manual_process_alternative`, `do_nothing_alternative`: 100%
    deterministic, generic category templates (no Gemini involvement at all).

`entries` is kept as a deprecated flat-list alias (verified + unverified_possibilities + indirect +
manual + do_nothing, in that order) for any consumer still reading the pre-Phase-B shape.
"""

from __future__ import annotations

AGENT_VERSION = "v3-typed-possibilities"

_INDIRECT_ALTERNATIVE_TEMPLATE = "Other {industry} tools/products serving a similar customer"
_MANUAL_PROCESS_DESCRIPTION = "Manual or spreadsheet-based process (status quo alternative)"
_DO_NOTHING_DESCRIPTION = "Doing nothing / no solution adopted"

_UNKNOWN_FIELDS_FOR_NAMED = [
    "category", "comparable_capability", "likely_strength", "likely_weakness", "differentiation_gap",
]


def _verified_competitor_entry(name: str) -> dict:
    return {
        "name": name,
        "verification_status": "unverified_by_system",
        "category": "user-named competitor (not independently verified)",
        "comparable_capability": "unknown — no verified product/feature data available",
        "likely_strength": "unknown — requires independent research",
        "likely_weakness": "unknown — requires independent research",
        "differentiation_gap": "unknown — requires direct comparison research",
        "evidence_source": "user-submitted (market_evidence.known_competitors)",
        "confidence": "low",
        "unknown_fields": _UNKNOWN_FIELDS_FOR_NAMED,
    }


def _unverified_possibility_entry(possibility: dict) -> dict:
    """`possibility` is one already-validated, already-safety-checked item from
    app.agents.competitor_reviewer.suggest_competitor_possibilities_safely — see
    app.ai.schemas.GeminiCompetitorPossibility. No further sanitization happens here; this
    function's only job is reshaping the typed reviewer output into this bucket's entry shape."""
    return {
        "category": possibility["category"],
        "solution_type": possibility["solution_type"],
        "reason": possibility["reason"],
        "evidence_source": "gemini-suggested category (advisory, never a named company)",
        "confidence": "low",
    }


def _indirect_alternative_entry(industry_label: str) -> dict:
    return {
        "category": _INDIRECT_ALTERNATIVE_TEMPLATE.format(industry=industry_label),
        "evidence_source": "derived category (no user-submitted competitor names)",
        "confidence": "low",
    }


def generate_competitor_analysis(
    known_competitors: list[str],
    industry_prediction: dict | None,
    unverified_possibilities: list[dict] | None = None,
) -> dict:
    industry_label = (industry_prediction or {}).get("predicted_industry") or "this"

    verified_competitors = [_verified_competitor_entry(name) for name in known_competitors]
    unverified_possibilities_bucket = [
        _unverified_possibility_entry(p) for p in (unverified_possibilities or [])
    ]
    indirect_alternatives = [_indirect_alternative_entry(industry_label)]
    manual_process_alternative = {
        "description": _MANUAL_PROCESS_DESCRIPTION,
        "evidence_source": "generic deterministic category",
        "confidence": "low",
    }
    do_nothing_alternative = {
        "description": _DO_NOTHING_DESCRIPTION,
        "evidence_source": "generic deterministic category",
        "confidence": "low",
    }

    recommended_action = (
        "Independently research each named competitor's actual product, pricing, and positioning "
        "— this system does not verify or fetch third-party company data."
        if known_competitors
        else "Identify and name 2-3 real, specific alternatives customers currently use."
    )

    def _generic_entry(label: str, evidence_source: str, confidence: str) -> dict:
        return {
            "competitor_or_alternative": label,
            "category": "generic alternative category (no named companies)",
            "comparable_capability": "unknown — category-level only, no specific product identified",
            "likely_strength": "unknown",
            "likely_weakness": "unknown",
            "differentiation_gap": "unknown — requires identifying and researching real named alternatives",
            "evidence_source": evidence_source,
            "confidence": confidence,
            "unknown_fields": ["comparable_capability", "likely_strength", "likely_weakness", "differentiation_gap"],
        }

    # Deprecated flat-list alias for any consumer still reading the pre-Phase-B `entries` shape —
    # preserves the exact old branching (named competitors OR the 3 generic categories), with any
    # Gemini-suggested possibilities appended on top when present.
    if known_competitors:
        entries = [
            {
                "competitor_or_alternative": e["name"],
                "category": e["category"],
                "comparable_capability": e["comparable_capability"],
                "likely_strength": e["likely_strength"],
                "likely_weakness": e["likely_weakness"],
                "differentiation_gap": e["differentiation_gap"],
                "evidence_source": e["evidence_source"],
                "confidence": e["confidence"],
                "unknown_fields": e["unknown_fields"],
            }
            for e in verified_competitors
        ]
    else:
        entries = (
            [_generic_entry(a["category"], a["evidence_source"], a["confidence"]) for a in indirect_alternatives]
            + [_generic_entry(manual_process_alternative["description"], manual_process_alternative["evidence_source"], manual_process_alternative["confidence"])]
            + [_generic_entry(do_nothing_alternative["description"], do_nothing_alternative["evidence_source"], do_nothing_alternative["confidence"])]
        )
    entries = entries + [_generic_entry(p["category"], p["evidence_source"], p["confidence"]) for p in unverified_possibilities_bucket]

    return {
        "agent_version": AGENT_VERSION,
        "verified_competitors": verified_competitors,
        "unverified_possibilities": unverified_possibilities_bucket,
        "indirect_alternatives": indirect_alternatives,
        "manual_process_alternative": manual_process_alternative,
        "do_nothing_alternative": do_nothing_alternative,
        # Deprecated alias — see module docstring. Kept for backward compatibility only; new
        # consumers should read the 5 named buckets above instead.
        "entries": entries,
        "recommended_validation_actions": [recommended_action],
        "disclaimer": (
            "No competitor database or web-search integration exists in this system. Real company "
            "names, pricing, market share, funding, or customer counts are never fabricated here — "
            "verified_competitors only ever echoes names the founder directly submitted (still "
            "unverified_by_system), unverified_possibilities is Gemini-advisory category-level "
            "only (empty without Gemini), and indirect_alternatives/manual_process_alternative/"
            "do_nothing_alternative are always deterministic, generic categories."
        ),
    }
