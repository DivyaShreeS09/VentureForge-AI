"""Deterministic revenue scenario calculator — NOT a trained ML model.

See ml/DATASETS.md "Revenue Estimation — Dataset Decision": every real Kaggle dataset candidate
inspected for startup revenue estimation was either self-declared synthetic, a well-known toy
regression set (50 rows), or otherwise unable to scientifically support a trained model at this
stage of a startup (a pre-revenue idea has no historical revenue to learn from in the first
place). Rather than fabricate a "trained revenue predictor," this module computes a transparent,
assumption-driven range: entirely deterministic, versioned, and never described as a prediction.

Phase A correction: a scenario is now *always* produced, even when the founder supplies zero
inputs — each of the 4 assumptions independently falls back to a centrally defined, versioned
default (app.ml.revenue_defaults), clearly labeled `assumption_source: "suggested_default"` and
never presented as a fact. `available: False` no longer exists; every field this module can't
compute a real number for either has real user input or an honestly-labeled suggested default.
"""

from __future__ import annotations

from app.ml.revenue_defaults import REVENUE_DEFAULTS_VERSION, resolve_default_assumptions

SCENARIO_ENGINE_VERSION = "v2-deterministic-with-defaults"

# Conservative/base/optimistic offsets applied as an additive delta around the resolved growth
# rate (not a multiplier) — a multiplier inverts scenario ordering for a negative growth rate
# (e.g. 0.7x of -10% is *less* negative than 1.3x of -10%), which would violate
# conservative <= base <= optimistic. An additive +/-30% delta preserves that ordering regardless
# of the growth rate's sign.
_SCENARIO_GROWTH_DELTA_FRACTION = 0.3
PROJECTION_MONTHS = 12

_FIELD_UNITS = {
    "price_per_customer_usd": "USD/month",
    "initial_customers": "customers",
    "monthly_growth_rate_pct": "%/month",
    "gross_margin_pct": "%",
}
_USER_SUPPLIED_EXPLANATION = "Founder-supplied assumption."

# Every field except growth rate must be non-negative — a negative price, customer count, or
# margin is never meaningful. `monthly_growth_rate_pct` is the one explicitly documented field
# where the scenario model supports contraction (a shrinking customer base), bounded at -100%
# (losing the entire customer base in a month) — see RevenueAssumptionsPatchRequest's matching
# `ge=-100` bound, which is the single source of truth for this limit.
_FIELD_MIN_VALUE = {
    "price_per_customer_usd": 0.0,
    "initial_customers": 0,
    "monthly_growth_rate_pct": -100.0,
    "gross_margin_pct": 0.0,
}


def _scenario_growth_rate(base_rate: float, scenario: str) -> float:
    delta = abs(base_rate) * _SCENARIO_GROWTH_DELTA_FRACTION
    if scenario == "conservative":
        return base_rate - delta
    if scenario == "optimistic":
        return base_rate + delta
    return base_rate


def _resolve_field(
    field: str, user_value: float | int | None, default_value: float | int, default_explanation: str
) -> dict:
    """Resolve one assumption field to `{value, unit, assumption_source, explanation, editable}`.
    A user-supplied value below this field's documented minimum (see `_FIELD_MIN_VALUE` — 0 for
    every field except growth rate, which permits contraction down to -100%) is treated as not
    supplied, falling back to the default rather than computing a nonsensical scenario. This
    should never actually trigger from the validated API schema, but this module is also callable
    directly.
    """
    if user_value is not None and user_value >= _FIELD_MIN_VALUE[field]:
        return {
            "value": user_value,
            "unit": _FIELD_UNITS[field],
            "assumption_source": "user_supplied",
            "explanation": _USER_SUPPLIED_EXPLANATION,
            "editable": True,
        }
    return {
        "value": default_value,
        "unit": _FIELD_UNITS[field],
        "assumption_source": "suggested_default",
        "explanation": default_explanation,
        "editable": True,
    }


def estimate_revenue_scenario(
    price_per_customer_usd: float | None,
    initial_customers: int | None,
    monthly_growth_rate_pct: float | None,
    gross_margin_pct: float | None,
    primary_domain: str | None = None,
    model_category_label: str | None = None,
) -> dict:
    """Always project a 12-month conservative/base/optimistic revenue range. Every one of the 4
    assumptions is independently resolved to either the founder's own value or a versioned,
    domain-aware suggested default (app.ml.revenue_defaults) — never fabricated as a fact, always
    labeled and editable in the response.
    """
    defaults, default_basis = resolve_default_assumptions(primary_domain, model_category_label)

    resolved = {
        "price_per_customer_usd": _resolve_field(
            "price_per_customer_usd", price_per_customer_usd, defaults["price_per_customer_usd"], defaults["explanation"]
        ),
        "initial_customers": _resolve_field(
            "initial_customers", initial_customers, defaults["initial_customers"], defaults["explanation"]
        ),
        "monthly_growth_rate_pct": _resolve_field(
            "monthly_growth_rate_pct",
            monthly_growth_rate_pct,
            defaults["monthly_growth_rate_pct"],
            defaults["explanation"],
        ),
        "gross_margin_pct": _resolve_field(
            "gross_margin_pct", gross_margin_pct, defaults["gross_margin_pct"], defaults["explanation"]
        ),
    }
    missing_assumptions = [
        field for field, entry in resolved.items() if entry["assumption_source"] == "suggested_default"
    ]

    price = resolved["price_per_customer_usd"]["value"]
    customers_start = resolved["initial_customers"]["value"]
    growth_pct = resolved["monthly_growth_rate_pct"]["value"]
    margin = resolved["gross_margin_pct"]["value"] / 100.0

    scenarios: dict[str, dict] = {}
    for scenario_name in ("conservative", "base", "optimistic"):
        scenario_growth = _scenario_growth_rate(growth_pct, scenario_name) / 100.0
        customers = customers_start
        monthly_revenue: list[float] = []
        for _ in range(PROJECTION_MONTHS):
            monthly_revenue.append(customers * price)
            customers = customers * (1 + scenario_growth)

        annual_revenue = sum(monthly_revenue)
        scenarios[scenario_name] = {
            "annual_revenue_usd": round(annual_revenue, 2),
            "annual_gross_profit_usd": round(annual_revenue * margin, 2),
            "month_12_customers": round(customers, 1),
            "month_12_monthly_revenue_usd": round(monthly_revenue[-1], 2),
        }

    return {
        "engine_version": SCENARIO_ENGINE_VERSION,
        "revenue_defaults_version": REVENUE_DEFAULTS_VERSION,
        "available": True,
        "default_basis": default_basis,
        "missing_assumptions": missing_assumptions,
        "assumptions": resolved,
        "scenarios": scenarios,
        # v1-compat: the old flat `assumptions_used` shape (bare numbers, no provenance) is kept
        # for any existing consumer that reads it directly — see the frontend's RevenueEstimate
        # type, which now prefers `assumptions` but still accepts this.
        "assumptions_used": {field: entry["value"] for field, entry in resolved.items()},
        "disclaimer": (
            "This is a calculator, not a prediction — it's not based on historical data and it's "
            "not a guarantee of what you'll actually make. Every number below is either one you "
            "gave me or a clearly labeled placeholder; look at each field to see which is which."
        ),
    }
