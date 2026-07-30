import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";
import { ForgeSequence } from "../../src/components/forge/ForgeSequence";
import { makeAnalysis } from "../testUtils/analysisFixture";

describe("ForgeSequence", () => {
  it("renders the fixed stage checklist even before any real stage arrives", () => {
    render(<ForgeSequence analysis={null} />);
    expect(screen.getByText("Reading Your Idea")).toBeInTheDocument();
    expect(screen.getByText("Preparing Your Mentor Report")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/reading what you've told me/i);
  });

  it("surfaces a real industry insight the moment it's available, never a fabricated one", () => {
    const analysis = makeAnalysis({
      current_stage: "Understanding Your Industry",
      industry_prediction: {
        predicted_industry: "b2b",
        confidence: 0.8,
        alternatives: [],
        model_version: "v1",
        explanation: { method: "", available: false, terms: [] },
        is_uncertain: false,
      },
    });
    render(<ForgeSequence analysis={analysis} />);
    expect(screen.getByRole("status")).toHaveTextContent(/looks like the b2b space/i);
  });

  it("hedges the insight when the backend itself is uncertain", () => {
    const analysis = makeAnalysis({
      current_stage: "Understanding Your Industry",
      industry_prediction: {
        predicted_industry: "b2b",
        confidence: 0.3,
        alternatives: [],
        model_version: "v1",
        explanation: { method: "", available: false, terms: [] },
        is_uncertain: true,
      },
    });
    render(<ForgeSequence analysis={analysis} />);
    expect(screen.getByRole("status")).toHaveTextContent(/this might be the b2b space/i);
  });

  it("falls back to the plain stage name when no specific insight field exists yet", () => {
    const analysis = makeAnalysis({ current_stage: "Checking Your Evidence" });
    render(<ForgeSequence analysis={analysis} />);
    expect(screen.getByRole("status")).toHaveTextContent(/checking your evidence/i);
  });

  it("surfaces the real value proposition during the longest merged market-study stage", () => {
    const analysis = makeAnalysis({
      current_stage: "Studying Your Market",
      business_model: {
        agent_version: "v1",
        value_proposition: "Cuts food waste for independent restaurants.",
        customer_segments: "",
        channels: "",
        customer_relationships: "",
        revenue_streams: "",
        key_resources: "",
        key_activities: "",
        key_partners: "",
        cost_structure: "",
        unit_economics_readiness: "",
        scalability: "",
        evidence_gaps: [],
        recommended_experiments: [],
        source_attribution: {},
        disclaimer: "",
      },
    });
    render(<ForgeSequence analysis={analysis} />);
    expect(screen.getByRole("status")).toHaveTextContent(/cuts food waste for independent restaurants/i);
  });

  it("surfaces the real top-ranked action during the growth-strategy stage", () => {
    const analysis = makeAnalysis({
      current_stage: "Mapping Your Growth Strategy",
      student3_outputs: {
        customer_segment: { segment_id: "", segment_name: "", fit_score: null, characteristics: [], pain_points: [], recommended_channels: [], evidence_basis: [], limitations: [], model_version: "v1", method: "unavailable" },
        ranked_actions: [
          { title: "Run a 2-week pilot with 3 restaurants", priority_score: 1, impact: "high", effort: "low", urgency: "now", evidence_basis: [], dependency: "", readiness_dimension: "" },
        ],
        innovation_opportunities: [],
        risks: [],
        growth_strategy: [],
        pitch_deck: [],
        executive_summary: [],
      },
    });
    render(<ForgeSequence analysis={analysis} />);
    expect(screen.getByRole("status")).toHaveTextContent(/run a 2-week pilot with 3 restaurants/i);
  });

  it("marks every stage done and shows the real overall assessment once completed", () => {
    const analysis = makeAnalysis({
      status: "COMPLETED",
      current_stage: "Preparing Your Mentor Report",
      current_node: "persistence",
      judge_summary: {
        overall_assessment: "A promising early-stage B2B opportunity.",
        strengths: [],
        weaknesses: [],
        missing_evidence: [],
        next_actions: [],
        confidence_level: "medium",
        source_attribution: {},
        suggested_possibilities: [],
        model_category: null,
        venture_positioning: null,
        taxonomy_candidates: [],
      },
    });
    render(<ForgeSequence analysis={analysis} />);
    expect(screen.getByRole("status")).toHaveTextContent(/a promising early-stage b2b opportunity/i);
  });

  it("shows an honest failure message when the request itself failed", () => {
    render(<ForgeSequence analysis={null} failed />);
    expect(screen.getByRole("status")).toHaveTextContent(/something interrupted the forging/i);
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<ForgeSequence analysis={makeAnalysis({ current_stage: "Scoring Your Readiness" })} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
