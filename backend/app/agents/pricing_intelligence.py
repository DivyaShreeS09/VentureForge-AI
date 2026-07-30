"""Pricing Intelligence (Product Intelligence Sprint, Phase 3).

Deterministic, additive, never touches app.ml.revenue_scenario's own tested numeric engine or
RevenueAssumptions — this module only ADDS a founder-facing pricing recommendation on top of the
same domain/category default already resolved by app.ml.revenue_defaults, adjusted for currency
and target market. Gemini may separately add qualitative `pricing_rationale` advice items (see
app.agents.mentor_reviewer) but never a specific price — every number here is deterministic and
traceable to a named heuristic, never fabricated market research.

Design constraints (explicit product requirement):
  - India is the primary assumed market. INR is the default currency whenever the founder's own
    words/evidence suggest an Indian market; USD only when there is real evidence of an
    international/non-India target.
  - Never claim a live market rate or a cited market study — the USD->INR reference rate and the
    India price-adjustment factor below are both disclosed, versioned heuristics, not live data.
  - When the underlying signal is weak (no domain-specific comparator, or target market itself is
    an assumption rather than founder-stated), return a RANGE, never a single confident number.
  - Every recommendation explains WHY: which domain comparator was used, what market was detected
    and from what evidence, and what adjustment was applied.
"""

from __future__ import annotations

import re

from app.ml.revenue_defaults import DOMAIN_BASIS, resolve_default_assumptions

PRICING_INTELLIGENCE_VERSION = "v1"

# Disclosed, versioned heuristics — NOT live FX data and NOT a cited market study. Both are
# deliberately conservative, round numbers so they never read as spuriously precise research.
#
# USD_TO_INR_REFERENCE_RATE: a reference approximation for converting the existing USD-denominated
# domain defaults (app.ml.revenue_defaults) into INR terms. Real FX rates fluctuate; this constant
# is intentionally NOT wired to a live API (this product never fabricates real-time market data) —
# it is a fixed, disclosed approximation, revisited only when this file is deliberately updated.
USD_TO_INR_REFERENCE_RATE = 83.0

# INDIA_WILLINGNESS_TO_PAY_FACTOR: Indian SaaS/software buyers commonly pay a lower nominal price
# than the US-anchored default even after currency conversion — a well-known, widely-discussed
# pattern in Indian SaaS pricing (not a specific cited dataset this product has access to, so it is
# never presented as one). Applied only to the currency-converted USD default, never claimed as a
# discount off a "real" price — the rationale text always names this as a heuristic adjustment.
INDIA_WILLINGNESS_TO_PAY_FACTOR = 0.45

# Range multipliers applied around a point estimate whenever confidence is not high — wide enough
# to be honest about the uncertainty, narrow enough to still be a useful anchor.
_RANGE_LOW_MULTIPLIER = 0.6
_RANGE_HIGH_MULTIPLIER = 1.6

_INDIA_KEYWORDS = (
    "india", "indian", "bharat", "bengaluru", "bangalore", "mumbai", "delhi", "ncr", "chennai",
    "hyderabad", "pune", "kolkata", "ahmedabad", "gurugram", "gurgaon", "noida", "inr", "rupee", "₹",
)
_INTERNATIONAL_KEYWORDS = (
    "united states", "u.s.", "america", "europe", "european", "united kingdom",
    "canada", "australia", "global market", "worldwide", "international customers", "usd", "dollar",
    "nigeria", "kenya", "brazil", "vietnam", "singapore", "indonesia", "philippines", "mexico",
    "germany", "france", "japan", "china", "southeast asia", "africa", "latin america",
)
# Short, ambiguous abbreviations that would false-positive as a substring match inside ordinary
# words (e.g. "us" inside "business", "uk" inside "truck", "usa" inside "usage") — matched with
# word boundaries only.
_INTERNATIONAL_WORD_BOUNDARY_KEYWORDS = ("us", "uk", "usa")


def _detect_target_market(startup_description: str, market_evidence: dict) -> dict:
    """Return {"market": "india"|"international"|"unclear", "is_assumption": bool,
    "evidence": list[str]} — never a fabricated signal; only ever what the founder's own words or
    submitted evidence actually contain, checked against two small, transparent keyword lists.

    Includes `market_evidence["geography"]` in the scanned text — a founder-supplied geography
    field (e.g. "United States", "Bengaluru, India") is direct target-market evidence and must not
    be silently ignored just because it wasn't repeated inside the free-text description.
    """
    haystack_parts = [
        startup_description or "",
        market_evidence.get("target_market") or "",
        market_evidence.get("customer_type") or "",
        market_evidence.get("geography") or "",
    ]
    haystack = " ".join(haystack_parts).lower()

    india_hits = [kw for kw in _INDIA_KEYWORDS if kw in haystack]
    intl_hits = [kw for kw in _INTERNATIONAL_KEYWORDS if kw in haystack]
    intl_hits += [
        kw for kw in _INTERNATIONAL_WORD_BOUNDARY_KEYWORDS
        if re.search(rf"\b{re.escape(kw)}\b", haystack)
    ]

    if india_hits and not intl_hits:
        return {"market": "india", "is_assumption": False, "evidence": india_hits}
    if intl_hits and not india_hits:
        return {"market": "international", "is_assumption": False, "evidence": intl_hits}
    if india_hits and intl_hits:
        # Both present (e.g. "expanding from India to the US") — genuinely mixed signal, not a
        # confident single-market call either way.
        return {"market": "unclear", "is_assumption": True, "evidence": india_hits + intl_hits}
    # No signal either way — per the product's explicit primary-market assumption, default to
    # India, but this is honestly disclosed as an assumption, not a detected fact.
    return {"market": "india", "is_assumption": True, "evidence": []}


PILOT_TIER_MULTIPLIER = 0.5
PREMIUM_TIER_MULTIPLIER = 2.0


def _build_tiers(anchor: float, venture_signals: dict | None) -> dict:
    """Product Intelligence Sprint (Adaptive pass): a single number/range answers "what should I
    charge," but a founder pricing an unproven product needs a path (pilot -> launch -> premium),
    not one static figure. Anchored on the same `anchor` value the point-estimate/range logic
    already computed — never a second, independently-fabricated number. `venture_signals` (real,
    already-computed facts: funding-readiness evidence states, not a new inference) only changes
    which tier is framed as "start here," never the underlying math.
    """
    signals = venture_signals or {}
    has_traction = bool(signals.get("has_traction"))
    has_prototype = bool(signals.get("has_prototype"))

    if has_traction:
        recommended_starting_tier = "launch"
        starting_tier_reason = "You already have real traction, so pricing at the launch tier (rather than a discounted pilot rate) is defensible now."
    elif has_prototype:
        recommended_starting_tier = "pilot"
        starting_tier_reason = "You have a working prototype but no confirmed traction yet — price a pilot low enough to remove cost as an objection while you prove the outcome."
    else:
        recommended_starting_tier = "pilot"
        starting_tier_reason = "With no prototype or traction confirmed yet, don't anchor on a number at all until a pilot validates the workflow — the pilot tier below is a placeholder for that conversation, not a quote to send out yet."

    return {
        # Rounded to whole currency units, never cents — a disclosed heuristic estimate (category
        # comparator + a fixed adjustment factor) implies far less precision than a cents-level
        # figure would suggest; found by the Startup Domain Intelligence Sprint's consistency audit
        # flagging "$2218.59"-style figures as implied false precision.
        "pilot": round(anchor * PILOT_TIER_MULTIPLIER),
        "launch": round(anchor),
        "premium": round(anchor * PREMIUM_TIER_MULTIPLIER),
        "recommended_starting_tier": recommended_starting_tier,
        "starting_tier_reason": starting_tier_reason,
    }


def build_pricing_intelligence(
    venture_positioning: dict | None,
    model_category: dict | None,
    market_evidence: dict | None,
    startup_description: str,
    venture_signals: dict | None = None,
) -> dict:
    """Produce the founder-facing pricing recommendation. Always returns a complete dict — never
    `None` — mirroring app.ml.revenue_scenario's "always produce a scenario" design.

    `venture_signals` (optional): real, already-computed facts about THIS venture — funding-
    readiness evidence states, founder-submitted customer_type/startup_stage, named competitors —
    assembled once in app.agents.mentor_synthesis and threaded through so the recommendation can
    reference this founder's own inputs rather than only a category-level comparator. Category is
    still used as the underlying price comparator (no better source exists for "what does this kind
    of product typically cost"), but is now explicitly the weaker, secondary signal — venture_signals
    drive the tier/framing choice and the personalization notes below.
    """
    market_evidence = market_evidence or {}
    primary_domain = (venture_positioning or {}).get("primary_domain")
    model_category_label = (model_category or {}).get("label")

    base_defaults, basis = resolve_default_assumptions(primary_domain, model_category_label)
    base_usd = base_defaults["price_per_customer_usd"]
    domain_rationale = base_defaults["explanation"]
    has_specific_comparator = basis == DOMAIN_BASIS

    target = _detect_target_market(startup_description, market_evidence)

    if target["market"] == "india":
        currency = "INR"
        point_estimate = round(base_usd * USD_TO_INR_REFERENCE_RATE * INDIA_WILLINGNESS_TO_PAY_FACTOR)
        market_rationale = (
            "Evidence in the founder's own description/answers points to an Indian market "
            f"(matched: {', '.join(target['evidence'])}) — recommending INR pricing."
            if not target["is_assumption"]
            else "No explicit target-market evidence was given; India is this product's assumed "
            "primary market, so INR is recommended by default — correct this if you're targeting "
            "elsewhere."
        )
        adjustment_rationale = (
            f"Converted the USD comparator at an approximate reference rate of "
            f"₹{USD_TO_INR_REFERENCE_RATE:.0f}/$1, then applied a {INDIA_WILLINGNESS_TO_PAY_FACTOR:.0%} "
            "adjustment reflecting that Indian software buyers commonly pay a lower nominal price "
            "than the US-anchored comparator — a disclosed heuristic, not a cited market study."
        )
    elif target["market"] == "international":
        currency = "USD"
        point_estimate = base_usd
        market_rationale = (
            "Evidence in the founder's own description/answers points to an international/"
            f"non-India market (matched: {', '.join(target['evidence'])}) — recommending USD "
            "pricing, unadjusted."
        )
        adjustment_rationale = "No currency conversion or market adjustment applied."
    else:  # "unclear" — genuinely mixed signal
        currency = "USD/INR"
        point_estimate = base_usd
        market_rationale = (
            "The founder's own description mentions both Indian and international market signals "
            f"({', '.join(target['evidence'])}) — this looks like a multi-market venture, so no "
            "single currency is recommended yet. Figures below are shown in USD as the comparator "
            "currency; convert using the same heuristic above if pricing for India specifically."
        )
        adjustment_rationale = "No single-market adjustment applied — genuinely mixed evidence."

    # A single confident number is only honest when the domain comparator itself is specific AND
    # the target market was actually detected (not assumed) AND it resolved to exactly one market.
    is_confident = has_specific_comparator and not target["is_assumption"] and target["market"] in (
        "india", "international",
    )

    personalization = []
    signals = venture_signals or {}
    if signals.get("customer_type"):
        personalization.append(f"You described your customer as: \"{signals['customer_type']}\" — price relative to what that specific buyer already spends solving this problem manually, not just the category average below.")
    if signals.get("known_competitors"):
        personalization.append(
            f"You already listed {', '.join(signals['known_competitors'][:3])} as alternatives — "
            "find out what they actually charge before finalizing your own number; undercutting "
            "blindly is as risky as overpricing blindly."
        )
    if signals.get("revenue_streams") and "placeholder" not in str(signals.get("revenue_streams")).lower():
        personalization.append(f"Your business-model answers already imply: {signals['revenue_streams']} — reconcile that with the comparator-based figures below rather than treating them as two unrelated numbers.")

    result = {
        "pricing_intelligence_version": PRICING_INTELLIGENCE_VERSION,
        "currency": currency,
        "target_market": target["market"],
        "target_market_is_assumption": target["is_assumption"],
        "confidence": "high" if is_confident else "low",
        "rationale": [domain_rationale, market_rationale, adjustment_rationale],
        "pricing_tiers": _build_tiers(point_estimate, venture_signals),
        "personalization": personalization,
        "source": "deterministic heuristic (category comparator as a secondary signal; this founder's own evidence drives tier/framing) — never live market data or a cited study",
        # Startup Domain Intelligence Sprint, Phase 6 — explicit disclosure that this figure is
        # NOT retrieval-backed: app.ml.venture_retrieval's own corpus has no pricing/revenue field
        # for any company (see its UNSUPPORTED_DIMENSIONS), so no retrieved-evidence pricing claim
        # is ever possible here, regardless of confidence — stated plainly rather than implied.
        "evidence_used": (
            "None from retrieval — this project's retrieved-venture dataset has no pricing/revenue "
            "field for any company, so pricing can never be retrieval-backed. This figure is a "
            "deterministic category-comparator heuristic plus this founder's own submitted evidence, "
            "not evidence from similar real ventures' actual prices."
        ),
    }

    if is_confident:
        result["recommended_price_per_customer"] = point_estimate
        result["recommended_price_range"] = None
    else:
        result["recommended_price_per_customer"] = None
        result["recommended_price_range"] = {
            "low": round(point_estimate * _RANGE_LOW_MULTIPLIER),
            "high": round(point_estimate * _RANGE_HIGH_MULTIPLIER),
        }
        result["rationale"].append(
            "Shown as a range rather than one number because "
            + (
                "the target market isn't confidently established yet"
                if not has_specific_comparator or target["market"] not in ("india", "international")
                else "there's no specific pricing comparator for this exact category yet"
            )
            + " — narrow it down as you gather more evidence."
        )

    return result
