import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnalysisResult } from "../src/components/results/AnalysisResult";
import type { Analysis } from "../src/types/api";
import { buildAnalysis } from "./fixtures/analysisFixtures";

describe("AnalysisResult — Founder Decision Studio journey", () => {
  it("renders the full guided journey in order, once each, with the startup name", () => {
    render(<AnalysisResult analysis={buildAnalysis()} startupName="WasteLess" />);

    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual([
      "WasteLess",
      "Why This Startup Matters",
      "Founder Decision Panel",
      "90-Day Founder Roadmap",
      "Validation Plan",
      "Market Expansion",
      "Risk Dashboard",
      "Investment Readiness",
      "Founder Mentor",
    ]);
  });

  it("shows the startup snapshot fields (the same domain also mirrors into the collapsed Advanced detail, by design)", () => {
    render(<AnalysisResult analysis={buildAnalysis()} startupName="WasteLess" />);
    expect(screen.getAllByText("Restaurant Operations Technology").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Independent restaurant owners.")).toBeInTheDocument();
    // Shown in both the Startup Snapshot and Investment Readiness — two glances at the same
    // signal, by design, not a duplicated fact elsewhere in the journey.
    expect(screen.getAllByText("Insufficient input reliability").length).toBeGreaterThanOrEqual(1);
  });

  it("renders exactly one Founder Decision Panel recommendation", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    // developing readiness, no confirmed_risk items in the fixture -> "Proceed Carefully"
    expect(screen.getByText("Proceed Carefully")).toBeInTheDocument();
    expect(screen.queryByText("Should Build")).not.toBeInTheDocument();
    expect(screen.queryByText("High Risk")).not.toBeInTheDocument();
  });

  it("reorganizes the roadmap into First Week / First Month / Next 90 Days", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    expect(screen.getByText("First Week")).toBeInTheDocument();
    expect(screen.getByText("First Month")).toBeInTheDocument();
    expect(screen.getByText("Next 90 Days")).toBeInTheDocument();
  });

  it("shows the validation plan with failure signal, estimated time, and expected learning", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    expect(screen.getByText("Is 'Traction' actually true/sufficient?")).toBeInTheDocument();
    expect(screen.getByText("Failure signal")).toBeInTheDocument();
    expect(screen.getByText("Estimated time")).toBeInTheDocument();
    expect(screen.getByText("Expected learning")).toBeInTheDocument();
  });

  it("presents Market Expansion once, combining Idea Expansion and Strategic Opportunity data without duplication", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    expect(screen.getAllByText("Market Expansion")).toHaveLength(1);
    // "Hotels" legitimately appears twice here — once as a customer segment (idea_expansion) and
    // once as an adjacent market (strategic_opportunity) — two different framings of real data,
    // not a duplicate rendering of the same fact.
    expect(screen.getAllByText("Hotels").length).toBe(2);
    expect(
      screen.getByText("Hotel kitchens face the same food-cost and inventory-waste problem restaurants do, just at larger scale."),
    ).toBeInTheDocument(); // adjacent market (strategic_opportunity) — richer reasoning, shown once
    expect(screen.getByText("Analytics Platform")).toBeInTheDocument(); // future evolution
  });

  it("renders the risk dashboard from strategic_risks combined with Phase 5 planning risks, never as a founder weakness", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    expect(screen.getByText("Market may be narrower than assumed")).toBeInTheDocument();
    // Phase 5 (Student 3) planning risk, shown alongside the strategic risk above.
    expect(screen.getByText("Unvalidated customer problem")).toBeInTheDocument();
    expect(screen.getByText("Planning risk")).toBeInTheDocument();
    // Two risk cards (one strategic, one planning) both show Owner/Status.
    expect(screen.getAllByText("Owner: Founder").length).toBe(2);
    expect(screen.getAllByText("Status: Open").length).toBe(2);
  });

  it("unifies investment readiness (funding + historical pattern signal + evidence quality)", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    expect(screen.getByText("45/100")).toBeInTheDocument();
    expect(screen.getByText("Evidence Quality")).toBeInTheDocument();
    expect(screen.getByText(/dimensions confirmed/)).toBeInTheDocument();
  });

  it("ends the Founder Mentor section with the required closing sentence and top 3 actions", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    expect(screen.getByText("Here are the three highest-impact actions I'd recommend this week.")).toBeInTheDocument();
    // This action also happens to equal mentor_verdict.immediate_priority shown in the Founder
    // Decision Panel earlier — same underlying prioritized action, not a duplicate presentation.
    expect(screen.getAllByText("Secure one concrete pilot commitment before building further.").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Price the offering to 3 prospective customers.")).toBeInTheDocument();
    expect(screen.getByText("Compare against the 2 closest alternatives.")).toBeInTheDocument();
  });

  it("keeps the Advanced section collapsed by default and contains the technical detail", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    const advancedDetails = screen.getByText(/Advanced: How We Got This/).closest("details") as HTMLDetailsElement;
    expect(advancedDetails.open).toBe(false);
    expect(screen.getByText("Industry Classification Detail")).toBeInTheDocument();
    expect(screen.getByText("Evidence Matrix")).toBeInTheDocument();
  });

  it("never shows a source/provenance badge in the founder journey", () => {
    render(<AnalysisResult analysis={buildAnalysis()} />);
    // The founder journey sections (everything above the collapsed Advanced <details>) must never
    // show a raw provenance label — check the DOM outside of the <details> element.
    const advancedDetails = screen.getByText(/Advanced: How We Got This/).closest("details") as HTMLDetailsElement;
    const journeyRoot = advancedDetails.parentElement as HTMLElement;
    const journeyText = Array.from(journeyRoot.childNodes)
      .filter((n) => n !== advancedDetails)
      .map((n) => (n as HTMLElement).textContent ?? "")
      .join(" ");
    expect(journeyText).not.toMatch(/Deterministic Assessment|ML Prediction|Judge Synthesis/);
  });

  it("shows a failure banner when status is FAILED", () => {
    const failed: Analysis = { ...buildAnalysis(), status: "FAILED", error_message: "boom" };
    render(<AnalysisResult analysis={failed} />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
  });

  it("flags an uncertain classification in Advanced instead of presenting it as settled fact", () => {
    const uncertain = buildAnalysis({
      industry_prediction: {
        predicted_industry: "fintech",
        confidence: 0.28,
        alternatives: [],
        model_version: "v1",
        explanation: { method: "linear_coefficient_x_tfidf", available: false, terms: [] },
        is_uncertain: true,
        uncertainty_reasons: ["Top prediction confidence (0.28) is below the minimum reporting threshold (0.35)."],
      },
    });
    render(<AnalysisResult analysis={uncertain} />);
    expect(screen.getByText(/Uncertain classification/)).toBeInTheDocument();
    expect(screen.getByText(/below the minimum reporting threshold/)).toBeInTheDocument();
  });

  it("renders an optional AI narrative section in Advanced, clearly labeled as supplementary", () => {
    const withNarrative = buildAnalysis();
    withNarrative.judge_summary!.llm_narrative = {
      executive_summary: "A promising early concept with clear problem framing.",
      strategic_observations: ["Consider partnering with an existing POS vendor."],
      strengths: [],
      weaknesses: [],
      recommendations: [],
    };
    render(<AnalysisResult analysis={withNarrative} />);
    expect(screen.getByText(/AI-Generated Narrative/)).toBeInTheDocument();
    expect(screen.getByText(/promising early concept/)).toBeInTheDocument();
  });

  it("omits sections gracefully when idea_expansion/strategic_opportunity are absent", () => {
    const minimal = buildAnalysis({ idea_expansion: null, strategic_opportunity: null });
    render(<AnalysisResult analysis={minimal} />);
    expect(screen.getByText("Market Expansion")).toBeInTheDocument();
    expect(screen.getByText("No additional customer segments identified for this run.")).toBeInTheDocument();
    expect(screen.queryByText("Risk Dashboard")).not.toBeInTheDocument();
  });
});
