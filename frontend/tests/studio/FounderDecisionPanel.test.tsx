import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FounderDecisionPanel } from "../../src/components/results/studio/FounderDecisionPanel";
import { buildMentorInterpretation } from "../fixtures/analysisFixtures";

describe("FounderDecisionPanel", () => {
  it("renders the recommendation label, the reason, and the explicit non-prediction disclaimer", () => {
    render(<FounderDecisionPanel mentor={buildMentorInterpretation()} />);
    expect(screen.getByText("Proceed Carefully")).toBeInTheDocument();
    expect(screen.getByText(/not a prediction of success or failure/)).toBeInTheDocument();
  });

  it("shows the supporting detail (strongest signal, biggest risk, immediate priority)", () => {
    render(<FounderDecisionPanel mentor={buildMentorInterpretation()} />);
    expect(screen.getByText(/A specific, well-defined problem is one of the strongest early signals\./)).toBeInTheDocument();
    expect(screen.getByText("Secure one concrete pilot commitment before building further.")).toBeInTheDocument();
  });
});
