"""Deterministic revenue scenario calculator — NOT a trained ML model.

See ml/DATASETS.md "Revenue Estimation — Dataset Decision": every real Kaggle dataset candidate
inspected for startup revenue estimation was either self-declared synthetic, a well-known toy
regression set (50 rows), or otherwise unable to scientifically support a trained model at this
stage of a startup (a pre-revenue idea has no historical revenue to learn from in the first
place). Rather than fabricate a "trained revenue predictor," this module computes a transparent,
user-assumption-driven range: entirely deterministic, versioned, and never described as a
prediction. If the user supplies no assumptions, no numeric range is invented — every field is
reported as unavailable.
"""

from __future__ import annotations

SCENARIO_ENGINE_VERSION = "v1-deterministic"

# Conservative/base/optimistic multipliers on the user's own stated growth-rate assumption — not
# derived from any dataset, just a fixed +/-30% band around the user's own number so the range
# reflects assumption uncertainty rather than a false point estimate.
_SCENARIO_GROWTH_MULTIPLIER = {"conservative": 0.7, "base": 1.0, "optimistic": 1.3}
PROJECTION_MONTHS = 12


def estimate_revenue_scenario(
    price_per_customer_usd: float | None,
    initial_customers: int | None,
    monthly_growth_rate_pct: float | None,
    gross_margin_pct: float | None,
) -> dict:
    """Project a 12-month revenue range from user-supplied assumptions only.

    Returns `available=False` with no numeric fields if the minimum required assumptions (price
    and initial customer count) are missing — a partial guess dressed up as a range would still be
    fabrication.
    """
    missing_assumptions: list[str] = []
    if price_per_customer_usd is None:
        missing_assumptions.append("price_per_customer_usd")
    if initial_customers is None:
        missing_assumptions.append("initial_customers")

    if price_per_customer_usd is None or initial_customers is None:
        return {
            "engine_version": SCENARIO_ENGINE_VERSION,
            "available": False,
            "missing_assumptions": missing_assumptions,
            "scenarios": None,
            "disclaimer": (
                "Deterministic scenario calculator, not a trained model — no revenue range is "
                "shown because the minimum required assumptions (price per customer, initial "
                "customer count) were not supplied."
            ),
        }

    growth_rate = (monthly_growth_rate_pct or 0.0) / 100.0
    margin = (gross_margin_pct or 100.0) / 100.0
    if monthly_growth_rate_pct is None:
        missing_assumptions.append("monthly_growth_rate_pct")
    if gross_margin_pct is None:
        missing_assumptions.append("gross_margin_pct")

    scenarios: dict[str, dict] = {}
    for scenario_name, multiplier in _SCENARIO_GROWTH_MULTIPLIER.items():
        scenario_growth = growth_rate * multiplier
        customers = initial_customers
        monthly_revenue: list[float] = []
        for _ in range(PROJECTION_MONTHS):
            monthly_revenue.append(customers * price_per_customer_usd)
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
        "available": True,
        "missing_assumptions": missing_assumptions,
        "scenarios": scenarios,
        "assumptions_used": {
            "price_per_customer_usd": price_per_customer_usd,
            "initial_customers": initial_customers,
            "monthly_growth_rate_pct": monthly_growth_rate_pct or 0.0,
            "gross_margin_pct": gross_margin_pct if gross_margin_pct is not None else 100.0,
        },
        "disclaimer": (
            "Deterministic scenario calculator based entirely on the assumptions you supplied — "
            "not a trained prediction model, not historical data, and not a guarantee of actual "
            "revenue. Missing assumptions were defaulted (0% growth and/or 100% margin) and are "
            "listed in missing_assumptions."
        ),
    }
