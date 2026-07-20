import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WhyThisMatters } from "../../src/components/results/studio/WhyThisMatters";
import { buildMentorInterpretation } from "../fixtures/analysisFixtures";

describe("WhyThisMatters", () => {
  it("renders at most 6 bullets", () => {
    render(<WhyThisMatters mentor={buildMentorInterpretation()} marketIntelligence={null} />);
    expect(screen.getAllByRole("listitem").length).toBeLessThanOrEqual(6);
  });

  it("covers problem, customer, market need, and current opportunity", () => {
    render(<WhyThisMatters mentor={buildMentorInterpretation()} marketIntelligence={null} />);
    expect(screen.getByText(/Problem: Food waste eats into thin margins\./)).toBeInTheDocument();
    expect(screen.getByText(/Customer: Independent restaurant owners\./)).toBeInTheDocument();
    expect(screen.getByText(/Current opportunity:/)).toBeInTheDocument();
  });

  it("prefers real market intelligence over the mentor's generic customer_and_market fallback", () => {
    render(
      <WhyThisMatters
        mentor={buildMentorInterpretation()}
        marketIntelligence={{
          agent_version: "v1", market_summary: "Targets the SMB restaurant market.", opportunity_drivers: [],
          constraints: [], evidence_gaps: [], market_maturity: "unknown", confidence: "low",
          source_attribution: {}, recommended_validation_actions: [], disclaimer: "d",
        }}
      />,
    );
    expect(screen.getByText(/Targets the SMB restaurant market\./)).toBeInTheDocument();
  });
});
