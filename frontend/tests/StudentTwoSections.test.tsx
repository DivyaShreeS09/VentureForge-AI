import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnalysisResult } from "../src/components/results/AnalysisResult";
import { buildAnalysis, buildMentorInterpretation } from "./fixtures/analysisFixtures";

describe("Student 2 data — folded into the Founder Decision Studio journey", () => {
  it("shows 'Not available for this run' for the Historical Pattern Signal when success_prediction is null", () => {
    const analysis = buildAnalysis({ success_prediction: null, success_model_version: null });
    render(<AnalysisResult analysis={analysis} />);
    expect(screen.getByRole("heading", { name: "Investment Readiness" })).toBeInTheDocument();
    expect(screen.getAllByText("Not available for this run").length).toBeGreaterThanOrEqual(1);
  });

  it("shows the real Historical Pattern Signal display value when present", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    expect(screen.getAllByText("Insufficient input reliability").length).toBeGreaterThanOrEqual(1);
  });

  it("surfaces market intelligence inside Why This Startup Matters, not as a separate raw section", () => {
    const analysis = buildAnalysis({
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
    });
    render(<AnalysisResult analysis={analysis} />);
    expect(screen.getByText(/Targets the 'SMB payments' market/)).toBeInTheDocument();
  });

  it("renders revenue scenarios inside Investment Readiness when present", () => {
    const analysis = buildAnalysis({
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
    });
    render(<AnalysisResult analysis={analysis} />);
    expect(screen.getByText("$10,000")).toBeInTheDocument();
    expect(screen.getByText("$15,000")).toBeInTheDocument();
    expect(screen.getByText("$20,000")).toBeInTheDocument();
  });

  it("renders customer personas in the Advanced section, not the founder journey", () => {
    const analysis = buildAnalysis({
      customer_personas: {
        agent_version: "v1-deterministic",
        personas: [
          {
            persona_name: "Primary Target Customer",
            customer_type: "restaurant owners",
            role_or_context: "restaurant owners",
            goal: "reduce food waste",
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
    });
    render(<AnalysisResult analysis={analysis} />);
    const advancedDetails = screen.getByText(/Advanced: How We Got This/).closest("details") as HTMLDetailsElement;
    expect(advancedDetails).toContainElement(screen.getByText("Primary Target Customer"));
  });

  it("shows business model as one consolidated field in the Startup Snapshot and Investment Readiness", () => {
    const analysis = buildAnalysis({
      mentor_interpretation: buildMentorInterpretation({ business_model: "A telehealth platform for chronic care." }),
    });
    render(<AnalysisResult analysis={analysis} />);
    expect(screen.getAllByText("A telehealth platform for chronic care.").length).toBeGreaterThanOrEqual(2);
  });
});
