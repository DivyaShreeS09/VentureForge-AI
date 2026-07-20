import type { RevenueScenario } from "../types/api";

/** Mirrors backend/app/ml/revenue_scenario.py's deterministic math exactly, so editing a
 * suggested-default assumption in the browser can recompute the three scenarios instantly
 * without a round trip — this is a read-only, client-side preview recalculation only; the
 * founder's edits are never persisted unless a future save action calls the backend directly
 * with new RevenueAssumptions (this component does not do that yet). An additive +/-30% growth
 * delta (not a multiplier) is used so conservative <= base <= optimistic holds for a negative
 * growth rate too — see the backend module's own comment for why a multiplier would invert that
 * ordering.
 */

const SCENARIO_GROWTH_DELTA_FRACTION = 0.3;
const PROJECTION_MONTHS = 12;

function scenarioGrowthRate(baseRatePct: number, scenario: "conservative" | "base" | "optimistic"): number {
  const delta = Math.abs(baseRatePct) * SCENARIO_GROWTH_DELTA_FRACTION;
  if (scenario === "conservative") return baseRatePct - delta;
  if (scenario === "optimistic") return baseRatePct + delta;
  return baseRatePct;
}

export function recalculateScenarios(
  pricePerCustomerUsd: number,
  initialCustomers: number,
  monthlyGrowthRatePct: number,
  grossMarginPct: number,
): { conservative: RevenueScenario; base: RevenueScenario; optimistic: RevenueScenario } {
  const margin = grossMarginPct / 100;
  const build = (scenario: "conservative" | "base" | "optimistic"): RevenueScenario => {
    const growthRate = scenarioGrowthRate(monthlyGrowthRatePct, scenario) / 100;
    let customers = initialCustomers;
    let annualRevenue = 0;
    let lastMonthlyRevenue = 0;
    for (let i = 0; i < PROJECTION_MONTHS; i++) {
      lastMonthlyRevenue = customers * pricePerCustomerUsd;
      annualRevenue += lastMonthlyRevenue;
      customers = customers * (1 + growthRate);
    }
    return {
      annual_revenue_usd: Math.round(annualRevenue * 100) / 100,
      annual_gross_profit_usd: Math.round(annualRevenue * margin * 100) / 100,
      month_12_customers: Math.round(customers * 10) / 10,
      month_12_monthly_revenue_usd: Math.round(lastMonthlyRevenue * 100) / 100,
    };
  };
  return { conservative: build("conservative"), base: build("base"), optimistic: build("optimistic") };
}
