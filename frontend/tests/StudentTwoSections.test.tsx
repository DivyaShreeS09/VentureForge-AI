import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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
    explanation: { method: "linear_coefficient_x_tfidf", available: false, terms: [] },
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
  success_model_version: "v1",
  success_prediction: null,
  revenue_engine_version: "v1-deterministic",
  revenue_estimate: null,
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
  },
  workflow_trace: [],
  error_message: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("Student 2 result sections — unavailable states", () => {
  it("shows the model-unavailable message when success_prediction is null", () => {
    render(<AnalysisResult analysis={baseAnalysis} />);
    expect(screen.getByText(/Success prediction model unavailable for this run/)).toBeInTheDocument();
  });

  it("does not render market intelligence / competitor / persona / business model sections when null", () => {
    render(<AnalysisResult analysis={baseAnalysis} />);
    expect(screen.queryByText("Market Intelligence")).not.toBeInTheDocument();
    expect(screen.queryByText("Competitor Analysis")).not.toBeInTheDocument();
    expect(screen.queryByText("Customer Personas")).not.toBeInTheDocument();
    expect(screen.queryByText("Business Model")).not.toBeInTheDocument();
  });
});

describe("Student 2 result sections — real data rendering", () => {
  const populated: Analysis = {
    ...baseAnalysis,
    success_prediction: {
      predicted_label: "success",
      success_probability: 0.62,
      model_version: "v1",
      model_pipeline: "hist_gradient_boosting",
      dataset_version: "v1-crunchbase-2013",
      missing_features: [],
      is_uncertain: false,
      uncertainty_reasons: [],
      disclaimer: "Historical pattern estimate — not a guarantee.",
    },
    revenue_estimate: {
      engine_version: "v1-deterministic",
      available: true,
      missing_assumptions: [],
      scenarios: {
        conservative: { annual_revenue_usd: 10000, annual_gross_profit_usd: 7000, month_12_customers: 120, month_12_monthly_revenue_usd: 900 },
        base: { annual_revenue_usd: 15000, annual_gross_profit_usd: 10500, month_12_customers: 150, month_12_monthly_revenue_usd: 1200 },
        optimistic: { annual_revenue_usd: 20000, annual_gross_profit_usd: 14000, month_12_customers: 200, month_12_monthly_revenue_usd: 1600 },
      },
      disclaimer: "Deterministic scenario calculator, not a trained model.",
    },
    market_intelligence: {
      agent_version: "v1-deterministic",
      market_summary: "Targets the 'SMB payments' market in USA.",
      opportunity_drivers: [],
      constraints: [],
      evidence_gaps: [],
      market_maturity: "unknown",
      confidence: "low",
      source_attribution: {},
      recommended_validation_actions: [],
      disclaimer: "No live market data source is integrated.",
    },
    competitor_analysis: {
      agent_version: "v1-deterministic",
      entries: [
        {
          competitor_or_alternative: "Acme Corp",
          category: "user-named competitor (not independently verified)",
          comparable_capability: "unknown",
          likely_strength: "unknown",
          likely_weakness: "unknown",
          differentiation_gap: "unknown",
          evidence_source: "user-submitted",
          confidence: "low",
          unknown_fields: [],
        },
      ],
      recommended_validation_actions: [],
      disclaimer: "No competitor database is integrated.",
    },
    customer_personas: {
      agent_version: "v1-deterministic",
      personas: [
        {
          persona_name: "Primary Target Customer",
          customer_type: "clinic administrators",
          role_or_context: "clinic administrators",
          goal: "unknown",
          pain_point: "unknown",
          current_alternative: "unknown",
          decision_criteria: "unknown",
          adoption_barrier: "unknown",
          likely_channel: "unknown",
          evidence_source: "user-submitted",
          confidence: "medium",
          field_provenance: {},
          assumptions_requiring_validation: [],
        },
      ],
      disclaimer: "No demographic data is invented.",
    },
    business_model: {
      agent_version: "v1-deterministic",
      value_proposition: "A telehealth platform for chronic care.",
      customer_segments: "clinic administrators",
      channels: "unknown",
      customer_relationships: "unknown",
      revenue_streams: "unknown — no revenue_assumptions were submitted",
      key_resources: "unknown",
      key_activities: "unknown",
      key_partners: "unknown",
      cost_structure: "unknown",
      unit_economics_readiness: "not ready",
      scalability: "cannot be assessed",
      evidence_gaps: [],
      recommended_experiments: ["Test 1-2 candidate acquisition channels."],
      source_attribution: {},
      disclaimer: "No price, margin, CAC, LTV figure is invented.",
    },
  };

  it("renders the success prediction with real values", () => {
    render(<AnalysisResult analysis={populated} />);
    expect(screen.getByText("success")).toBeInTheDocument();
    expect(screen.getByText(/62% probability/)).toBeInTheDocument();
  });

  it("renders all three revenue scenarios", () => {
    render(<AnalysisResult analysis={populated} />);
    expect(screen.getByText("$10,000")).toBeInTheDocument();
    expect(screen.getByText("$15,000")).toBeInTheDocument();
    expect(screen.getByText("$20,000")).toBeInTheDocument();
  });

  it("renders market intelligence summary", () => {
    render(<AnalysisResult analysis={populated} />);
    expect(screen.getByText(/Targets the 'SMB payments' market/)).toBeInTheDocument();
  });

  it("renders competitor entries", () => {
    render(<AnalysisResult analysis={populated} />);
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
  });

  it("renders customer personas", () => {
    render(<AnalysisResult analysis={populated} />);
    expect(screen.getByText("Primary Target Customer")).toBeInTheDocument();
  });

  it("renders business model fields", () => {
    render(<AnalysisResult analysis={populated} />);
    expect(screen.getByText("A telehealth platform for chronic care.")).toBeInTheDocument();
    expect(screen.getByText("Test 1-2 candidate acquisition channels.")).toBeInTheDocument();
  });
});
