"""Centrally defined, versioned default revenue assumptions (Phase A: revenue always-scenario).

No public dataset defensibly supports a trained revenue predictor at idea-stage (see
ml/DATASETS.md) — these are hand-curated, plausible starting points, never described as trained or
as facts. Keyed primarily by `venture_positioning.primary_domain` (the founder-facing identity,
see app.agents.venture_positioning); if a domain has no entry here, falls back to a
`model_category`-keyed default (the raw 7-label ML category); if neither matches, falls back to a
single generic, clearly labeled discovery-stage default. This resolution order — never `available:
False` — is what lets app.ml.revenue_scenario always produce a scenario.
"""

from __future__ import annotations

REVENUE_DEFAULTS_VERSION = "v1"

GENERIC_DISCOVERY_STAGE_BASIS = "generic_discovery_stage_default"
DOMAIN_BASIS = "domain_default"
MODEL_CATEGORY_BASIS = "model_category_default"

# domain (from app.ml.positioning_taxonomy.POSITIONING_TAXONOMY) -> plausible starting assumptions.
# Every number here is a hand-picked, defensible starting point for a very early-stage venture in
# that domain — not derived from any dataset, and always presented as editable/overridable.
_DOMAIN_DEFAULTS: dict[str, dict] = {
    "Smart Facilities Technology": {
        "price_per_customer_usd": 500.0,
        "initial_customers": 3,
        "monthly_growth_rate_pct": 8.0,
        "gross_margin_pct": 65.0,
        "explanation": "Facilities buyers typically pay a monthly per-building monitoring fee; a "
        "handful of pilot buildings is a realistic starting count.",
    },
    "PropTech": {
        "price_per_customer_usd": 400.0,
        "initial_customers": 4,
        "monthly_growth_rate_pct": 6.0,
        "gross_margin_pct": 70.0,
        "explanation": "Property-management software is commonly priced per building/unit-portfolio.",
    },
    "Clinical Decision Support": {
        "price_per_customer_usd": 2000.0,
        "initial_customers": 1,
        "monthly_growth_rate_pct": 5.0,
        "gross_margin_pct": 75.0,
        "explanation": "Institutional (clinic/hospital) sales cycles are slow but high-value per "
        "account — one early institutional pilot is a realistic starting point.",
    },
    "Remote Patient Monitoring": {
        "price_per_customer_usd": 150.0,
        "initial_customers": 10,
        "monthly_growth_rate_pct": 10.0,
        "gross_margin_pct": 55.0,
        "explanation": "Per-patient-monitored monthly pricing is standard in remote monitoring.",
    },
    "HealthTech Diagnostics": {
        "price_per_customer_usd": 1500.0,
        "initial_customers": 1,
        "monthly_growth_rate_pct": 5.0,
        "gross_margin_pct": 70.0,
        "explanation": "Diagnostic tools are usually sold institutionally, priced per clinic/site.",
    },
    "Campus & Student Services": {
        "price_per_customer_usd": 5.0,
        "initial_customers": 200,
        "monthly_growth_rate_pct": 15.0,
        "gross_margin_pct": 80.0,
        "explanation": "Student-facing tools are typically low-price, high-volume (per-student or "
        "per-semester), with fast organic growth within one campus.",
    },
    "Peer Collaboration Marketplaces": {
        "price_per_customer_usd": 0.0,
        "initial_customers": 300,
        "monthly_growth_rate_pct": 20.0,
        "gross_margin_pct": 90.0,
        "explanation": "Free-to-students marketplaces monetize elsewhere (organizer tier) — the "
        "starting price here is $0, reflecting free individual usage during the growth phase.",
    },
    "EdTech": {
        "price_per_customer_usd": 15.0,
        "initial_customers": 100,
        "monthly_growth_rate_pct": 10.0,
        "gross_margin_pct": 75.0,
        "explanation": "Per-learner monthly subscription is a common EdTech starting model.",
    },
    "Restaurant Operations Technology": {
        "price_per_customer_usd": 99.0,
        "initial_customers": 5,
        "monthly_growth_rate_pct": 8.0,
        "gross_margin_pct": 70.0,
        "explanation": "A flat monthly SaaS fee per restaurant location, priced to sit comfortably "
        "next to existing POS software costs.",
    },
    "Food-Cost Management": {
        "price_per_customer_usd": 79.0,
        "initial_customers": 5,
        "monthly_growth_rate_pct": 8.0,
        "gross_margin_pct": 70.0,
        "explanation": "Similar per-location monthly pricing to Restaurant Operations Technology.",
    },
    "Productivity Software": {
        "price_per_customer_usd": 8.0,
        "initial_customers": 50,
        "monthly_growth_rate_pct": 12.0,
        "gross_margin_pct": 80.0,
        "explanation": "Consumer productivity apps commonly use a low-price monthly subscription.",
    },
    "General Consumer App": {
        "price_per_customer_usd": 5.0,
        "initial_customers": 50,
        "monthly_growth_rate_pct": 10.0,
        "gross_margin_pct": 75.0,
        "explanation": "A generic low-price consumer subscription starting point.",
    },
}

# Fallback keyed by the raw `model_category` label (app.ml.predictor's 7-label taxonomy), used
# only when `venture_positioning.primary_domain` has no entry above.
_MODEL_CATEGORY_DEFAULTS: dict[str, dict] = {
    "b2b": {
        "price_per_customer_usd": 200.0,
        "initial_customers": 5,
        "monthly_growth_rate_pct": 8.0,
        "gross_margin_pct": 70.0,
        "explanation": "A typical early-stage B2B SaaS per-seat/per-account monthly price.",
    },
    "healthcare": {
        "price_per_customer_usd": 1000.0,
        "initial_customers": 2,
        "monthly_growth_rate_pct": 5.0,
        "gross_margin_pct": 70.0,
        "explanation": "Institutional healthcare sales cycles are slow but high-value per account.",
    },
    "consumer": {
        "price_per_customer_usd": 10.0,
        "initial_customers": 100,
        "monthly_growth_rate_pct": 12.0,
        "gross_margin_pct": 75.0,
        "explanation": "A typical early-stage consumer subscription starting point.",
    },
    "industrials": {
        "price_per_customer_usd": 500.0,
        "initial_customers": 3,
        "monthly_growth_rate_pct": 6.0,
        "gross_margin_pct": 60.0,
        "explanation": "Industrial/B2B hardware-adjacent software is often priced per site/facility.",
    },
}

GENERIC_DISCOVERY_STAGE_DEFAULT: dict = {
    "price_per_customer_usd": 49.0,
    "initial_customers": 5,
    "monthly_growth_rate_pct": 5.0,
    "gross_margin_pct": 60.0,
    "explanation": "I don't have a specific starting point for your exact space yet, so this is a "
    "deliberately conservative discovery-stage placeholder — a rough starting point to edit, not a "
    "researched figure.",
}


def resolve_default_assumptions(
    primary_domain: str | None, model_category_label: str | None
) -> tuple[dict, str]:
    """Return `(defaults, basis)` where `basis` is one of `DOMAIN_BASIS`, `MODEL_CATEGORY_BASIS`,
    or `GENERIC_DISCOVERY_STAGE_BASIS` — always something, never `None`."""
    if primary_domain and primary_domain in _DOMAIN_DEFAULTS:
        return _DOMAIN_DEFAULTS[primary_domain], DOMAIN_BASIS
    normalized_category = (model_category_label or "").lower()
    if normalized_category in _MODEL_CATEGORY_DEFAULTS:
        return _MODEL_CATEGORY_DEFAULTS[normalized_category], MODEL_CATEGORY_BASIS
    return GENERIC_DISCOVERY_STAGE_DEFAULT, GENERIC_DISCOVERY_STAGE_BASIS
