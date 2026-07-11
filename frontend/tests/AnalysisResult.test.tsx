import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnalysisResult } from "../src/components/results/AnalysisResult";
import type { Analysis } from "../src/types/api";

const analysis: Analysis = {
  id: "analysis-1",
  startup_id: "startup-1",
  status: "COMPLETED",
  industry_model_version: "v1",
  industry_prediction: {
    predicted_industry: "fintech",
    confidence: 0.72,
    alternatives: [{ industry: "saas", confidence: 0.1 }],
    model_version: "v1",
    explanation: {
      method: "linear_coefficient_x_tfidf",
      available: true,
      terms: [{ term: "payments", contribution: 0.3, direction: "supports" }],
    },
  },
  funding_rubric_version: "v1",
  funding_assessment: {
    rubric_version: "v1",
    overall_score: 45,
    level: "developing",
    breakdown: [
      {
        dimension: "problem_clarity",
        label: "Problem Clarity",
        raw_score: 2,
        max_score: 2,
        weight: 0.14,
        weighted_contribution: 14,
        scale_description: "Specific, well-defined problem",
      },
    ],
    missing_evidence: ["Traction"],
    disclaimer: "This is a deterministic readiness assessment, not investment advice.",
  },
  judge_summary: {
    overall_assessment: "This startup was classified as 'fintech' and rated 'developing'.",
    strengths: ["Problem Clarity: Specific, well-defined problem"],
    weaknesses: [],
    missing_evidence: ["Traction"],
    next_actions: ["Recruit pilot users."],
    confidence_level: "medium",
    source_attribution: {},
  },
  workflow_trace: [],
  error_message: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("AnalysisResult", () => {
  it("renders industry, funding, and judge sections from real data", () => {
    render(<AnalysisResult analysis={analysis} />);

    expect(screen.getByText("fintech")).toBeInTheDocument();
    expect(screen.getByText(/72% confidence/)).toBeInTheDocument();
    expect(screen.getByText("payments")).toBeInTheDocument();

    expect(screen.getByText("45/100")).toBeInTheDocument();
    expect(screen.getByText("(developing)")).toBeInTheDocument();

    expect(screen.getByText(/classified as 'fintech'/)).toBeInTheDocument();
    // Appears twice by design: once as the Judge Verdict's highlighted "Immediate move", and
    // again in the full "Strategic Next Moves" list below it.
    expect(screen.getAllByText("Recruit pilot users.").length).toBeGreaterThanOrEqual(1);
  });

  it("shows a failure banner when status is FAILED", () => {
    render(<AnalysisResult analysis={{ ...analysis, status: "FAILED", error_message: "boom" }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
  });

  it("flags an uncertain classification instead of presenting it as settled fact", () => {
    const uncertainAnalysis: Analysis = {
      ...analysis,
      industry_prediction: {
        ...analysis.industry_prediction!,
        confidence: 0.28,
        is_uncertain: true,
        uncertainty_reasons: ["Top prediction confidence (0.28) is below the minimum reporting threshold (0.35)."],
      },
    };
    render(<AnalysisResult analysis={uncertainAnalysis} />);

    expect(screen.getByText(/Uncertain classification/)).toBeInTheDocument();
    expect(screen.getByText(/below the minimum reporting threshold/)).toBeInTheDocument();
  });

  it("does not show an uncertainty banner for a confident prediction", () => {
    render(<AnalysisResult analysis={analysis} />);
    expect(screen.queryByText(/Uncertain classification/)).not.toBeInTheDocument();
  });

  it("renders an optional AI narrative section, clearly labeled as supplementary", () => {
    const withNarrative: Analysis = {
      ...analysis,
      judge_summary: {
        ...analysis.judge_summary!,
        llm_narrative: {
          executive_summary: "A promising early fintech concept with clear problem framing.",
          strategic_observations: ["Consider partnering with an existing payments processor."],
          strengths: [],
          weaknesses: [],
          recommendations: [],
        },
      },
    };
    render(<AnalysisResult analysis={withNarrative} />);

    expect(screen.getByText(/AI-Generated Narrative/)).toBeInTheDocument();
    expect(screen.getByText(/promising early fintech concept/)).toBeInTheDocument();
  });

  it("omits the AI narrative section when no provider is configured", () => {
    render(<AnalysisResult analysis={analysis} />);
    expect(screen.queryByText(/AI-Generated Narrative/)).not.toBeInTheDocument();
  });

  it("collapses overlapping char-fragment explanation chips into their most informative form", () => {
    const withFragments: Analysis = {
      ...analysis,
      industry_prediction: {
        ...analysis.industry_prediction!,
        explanation: {
          method: "linear_coefficient_x_tfidf",
          available: true,
          terms: [
            { term: "robotics", kind: "word", contribution: 0.5, direction: "supports" },
            { term: "robot", kind: "char", contribution: 0.4, direction: "supports" },
            { term: "robo", kind: "char", contribution: 0.35, direction: "supports" },
            { term: "obot", kind: "char", contribution: 0.3, direction: "supports" },
            { term: "warehouse", kind: "word", contribution: 0.2, direction: "supports" },
          ],
        },
      },
    };
    render(<AnalysisResult analysis={withFragments} />);

    expect(screen.getByText("robotics")).toBeInTheDocument();
    expect(screen.getByText("warehouse")).toBeInTheDocument();
    expect(screen.queryByText("robot")).not.toBeInTheDocument();
    expect(screen.queryByText("robo")).not.toBeInTheDocument();
    expect(screen.queryByText("obot")).not.toBeInTheDocument();
  });
});
