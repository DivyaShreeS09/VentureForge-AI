import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisResult } from "../src/components/results/AnalysisResult";
import type { Analysis } from "../src/types/api";

const baseAnalysis: Analysis = {
  id: "analysis-1",
  startup_id: "startup-1",
  status: "COMPLETED",
  industry_model_version: "v1",
  industry_prediction: {
    predicted_industry: "fintech",
    confidence: 0.72,
    alternatives: [],
    model_version: "v1",
    explanation: { method: "linear_coefficient_x_tfidf", available: true, terms: [] },
  },
  funding_rubric_version: "v1",
  funding_assessment: {
    rubric_version: "v1",
    overall_score: 45,
    level: "developing",
    breakdown: [],
    missing_evidence: [],
    disclaimer: "This is a deterministic readiness assessment, not investment advice.",
  },
  success_model_version: null,
  success_prediction: null,
  revenue_engine_version: "v2-deterministic-with-defaults",
  revenue_estimate: {
    engine_version: "v2-deterministic-with-defaults",
    revenue_defaults_version: "v1",
    available: true,
    default_basis: "domain_default",
    missing_assumptions: ["price_per_customer_usd", "initial_customers", "monthly_growth_rate_pct", "gross_margin_pct"],
    assumptions: {
      price_per_customer_usd: { value: 99, unit: "USD/month", assumption_source: "suggested_default", explanation: "A starting point.", editable: true },
      initial_customers: { value: 5, unit: "customers", assumption_source: "suggested_default", explanation: "A starting point.", editable: true },
      monthly_growth_rate_pct: { value: 8, unit: "%/month", assumption_source: "suggested_default", explanation: "A starting point.", editable: true },
      gross_margin_pct: { value: 70, unit: "%", assumption_source: "suggested_default", explanation: "A starting point.", editable: true },
    },
    scenarios: {
      conservative: { annual_revenue_usd: 1000, annual_gross_profit_usd: 700, month_12_customers: 8, month_12_monthly_revenue_usd: 90 },
      base: { annual_revenue_usd: 1200, annual_gross_profit_usd: 840, month_12_customers: 10, month_12_monthly_revenue_usd: 120 },
      optimistic: { annual_revenue_usd: 1500, annual_gross_profit_usd: 1050, month_12_customers: 13, month_12_monthly_revenue_usd: 150 },
    },
    disclaimer: "Deterministic scenario calculator, not a trained model.",
  },
  market_intelligence: null,
  competitor_analysis: null,
  customer_personas: null,
  business_model: null,
  judge_summary: {
    overall_assessment: "This startup was classified as 'fintech' and rated 'developing'.",
    strengths: [],
    weaknesses: [],
    missing_evidence: [],
    next_actions: [],
    confidence_level: "medium",
    source_attribution: {},
    suggested_possibilities: [],
    model_category: { label: "fintech", confidence: 0.72, top_3: [], local_explanation: null, is_uncertain: false },
    venture_positioning: {
      primary_domain: "Payments Infrastructure",
      secondary_domains: [],
      deployment_sectors: [],
      confidence: 0.6,
      is_low_confidence: false,
      resolution_source: "taxonomy_dominant",
    },
    taxonomy_candidates: [],
    positioning_correction_rationale: null,
    gemini_rationale: null,
  },
  mentor_interpretation: {
    mentor_schema_version: "v1",
    source: "deterministic",
    idea_understanding: {
      summary: "PayFlux is building in the Payments Infrastructure space.",
      target_user: "Small businesses settling cross-border payments.",
      problem: "Cross-border settlement is slow.",
      proposed_solution: "A payments platform that settles in seconds.",
      business_context: "Positioned as Payments Infrastructure.",
    },
    venture_positioning: "Payments Infrastructure.",
    strengths: [],
    real_weaknesses: [],
    suggested_possibilities: [],
    founder_guidance_items: [],
    feature_gap_analysis: { present_capabilities: [], recommended_capabilities: [], premature_capabilities: [], not_relevant_capabilities: [] },
    customer_and_market: "No market intelligence was generated for this run.",
    business_model: "No business-model synthesis was generated for this run.",
    competitor_landscape: "No competitors were named by the founder.",
    revenue_scenarios: "See revenue_estimate for the full range.",
    mvp_recommendation: {
      target_user: "[Suggested] One small business.",
      single_core_problem: "[Suggested] The narrowest cross-border settlement case.",
      minimum_workflow: "[Suggested] Manual settlement for one corridor.",
      included_capabilities: [],
      excluded_for_now: [],
      success_metric: "[Suggested] Settlement time reduction.",
      pilot_environment: "[Suggested] One pilot corridor.",
      reasons: [],
    },
    validation_plan: [],
    roadmap_30_60_90: [
      { period: "days_1_30", focus: "Discovery", activities: [], rationale: "Validate first." },
      { period: "days_31_60", focus: "Build", activities: [], rationale: "Then build." },
      { period: "days_61_90", focus: "Launch", activities: [], rationale: "Then launch." },
    ],
    top_next_actions: ["Secure one pilot corridor."],
    mentor_verdict: {
      readiness_level: "developing",
      concise_verdict: "Developing — real progress alongside real gaps.",
      strongest_signal: "Problem is clear.",
      biggest_risk: "Traction not yet confirmed.",
      immediate_priority: "Secure one pilot corridor.",
    },
    evidence_and_uncertainty: {
      model_category_caveat: "model_category is technical evidence only.",
      historical_pattern_signal_caveat: "Loose historical comparison only.",
      low_confidence_flags: [],
      user_supplied_vs_suggested_summary: "All revenue figures are suggested defaults.",
      unresolved_questions: [],
    },
    source_attribution: {},
  },
  workflow_trace: [],
  error_message: null,
  positioning_correction_history: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function mockFetch(handlers: { taxonomy?: () => unknown; revenuePatch?: () => unknown | Promise<never> }) {
  return vi.fn((url: string) => {
    if (typeof url === "string" && url.includes("/taxonomy")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => handlers.taxonomy?.() ?? { taxonomy_version: "v1", domains: [], allowed_secondary_domains: [] },
      });
    }
    if (typeof url === "string" && url.includes("/revenue-assumptions")) {
      if (!handlers.revenuePatch) {
        return Promise.resolve({ ok: false, status: 500, json: async () => ({ detail: "server error" }) });
      }
      const result = handlers.revenuePatch();
      return Promise.resolve({ ok: true, status: 200, json: async () => result });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => ({ detail: "not found" }) });
  });
}

describe("AnalysisResult — taxonomy loading for positioning correction", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a loading state, then populates the dropdown from the live taxonomy endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        taxonomy: () => ({
          taxonomy_version: "v1",
          domains: [
            { id: "Payments Infrastructure", label: "Payments Infrastructure", description: "", deployment_sectors: [] },
            { id: "EdTech", label: "EdTech", description: "", deployment_sectors: [] },
          ],
          allowed_secondary_domains: ["Payments Infrastructure", "EdTech"],
        }),
      }),
    );

    render(<AnalysisResult analysis={baseAnalysis} />);
    expect(screen.getByText(/Loading available positioning domains/)).toBeInTheDocument();

    await waitFor(() => expect(screen.queryByText(/Loading available positioning domains/)).not.toBeInTheDocument());
    const select = screen.getByLabelText("Not the right industry?") as HTMLSelectElement;
    const optionValues = Array.from(select.options).map((o) => o.value);
    expect(optionValues).toEqual(["Payments Infrastructure", "EdTech"]);
  });

  it("degrades to a minimal fallback list and surfaces an error when the taxonomy fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("network down"))),
    );

    render(<AnalysisResult analysis={baseAnalysis} />);
    await waitFor(() => expect(screen.getByText(/Could not load the full taxonomy/)).toBeInTheDocument());

    const select = screen.getByLabelText("Not the right industry?") as HTMLSelectElement;
    expect(select.options.length).toBeGreaterThan(0);
  });
});

describe("AnalysisResult — revenue assumption save flow", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("distinguishes an unsaved edit preview from persisted values, and clears the banner on successful save", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        revenuePatch: () => ({
          ...baseAnalysis,
          revenue_estimate: {
            ...baseAnalysis.revenue_estimate,
            assumptions: {
              ...baseAnalysis.revenue_estimate!.assumptions,
              price_per_customer_usd: {
                value: 250,
                unit: "USD/month",
                assumption_source: "user_supplied",
                explanation: "Founder-supplied assumption.",
                editable: true,
              },
            },
          },
        }),
      }),
    );

    render(<AnalysisResult analysis={baseAnalysis} />);
    const priceInput = screen.getByLabelText("Price / customer") as HTMLInputElement;

    fireEvent.change(priceInput, { target: { value: "250" } });
    expect(screen.getByText(/Unsaved preview/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Save assumptions/ }));
    await waitFor(() => expect(screen.queryByText(/Unsaved preview/)).not.toBeInTheDocument());
    expect(screen.getByText("Founder-supplied")).toBeInTheDocument();
  });

  it("keeps the founder's draft visible and shows an error when the save request fails", async () => {
    vi.stubGlobal("fetch", mockFetch({}));

    render(<AnalysisResult analysis={baseAnalysis} />);
    const priceInput = screen.getByLabelText("Price / customer") as HTMLInputElement;
    fireEvent.change(priceInput, { target: { value: "310" } });

    fireEvent.click(screen.getByRole("button", { name: /Save assumptions/ }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());

    // The draft value must still be shown — a failed save must never silently discard it.
    expect((screen.getByLabelText("Price / customer") as HTMLInputElement).value).toBe("310");
  });
});
