import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarketExpansionSection } from "../../src/components/results/studio/MarketExpansionSection";
import { buildAnalysis } from "../fixtures/analysisFixtures";

describe("MarketExpansionSection", () => {
  it("renders all six subsections", () => {
    const analysis = buildAnalysis();
    render(<MarketExpansionSection ideaExpansion={analysis.idea_expansion!} strategicOpportunity={analysis.strategic_opportunity!} />);
    expect(screen.getByText("Customer Segments")).toBeInTheDocument();
    expect(screen.getByText("Adjacent Markets")).toBeInTheDocument();
    expect(screen.getByText("Expansion Paths")).toBeInTheDocument();
    expect(screen.getByText("Partnerships")).toBeInTheDocument();
    expect(screen.getByText("Pricing")).toBeInTheDocument();
    expect(screen.getByText("Future Evolution")).toBeInTheDocument();
  });

  it("sources Adjacent Markets from strategic_opportunity, not idea_expansion's own adjacent_industries", () => {
    const analysis = buildAnalysis();
    render(<MarketExpansionSection ideaExpansion={analysis.idea_expansion!} strategicOpportunity={analysis.strategic_opportunity!} />);
    // "Hotels" appears twice here by fixture design — once as a customer segment (idea_expansion)
    // and once as an adjacent market (strategic_opportunity); different framings, not a duplicate.
    expect(screen.getAllByText("Hotels").length).toBe(2);
    expect(
      screen.getByText("Hotel kitchens face the same food-cost and inventory-waste problem restaurants do, just at larger scale."),
    ).toBeInTheDocument();
  });

  it("degrades gracefully when both inputs are null", () => {
    render(<MarketExpansionSection ideaExpansion={null} strategicOpportunity={null} />);
    expect(screen.getByText("No additional customer segments identified for this run.")).toBeInTheDocument();
    expect(screen.getByText("No adjacent markets identified for this run.")).toBeInTheDocument();
  });
});
