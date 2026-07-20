import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FounderMentorSection } from "../../src/components/results/studio/FounderMentorSection";
import { buildMentorInterpretation } from "../fixtures/analysisFixtures";

describe("FounderMentorSection", () => {
  it("ends with the required closing sentence and exactly the top 3 actions", () => {
    render(<FounderMentorSection mentor={buildMentorInterpretation()} />);
    expect(screen.getByText("Here are the three highest-impact actions I'd recommend this week.")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("uses plain language — the idea summary and concise verdict, no technical terminology", () => {
    render(<FounderMentorSection mentor={buildMentorInterpretation()} />);
    expect(screen.getByText("WasteLess is building in the Restaurant Operations Technology space.")).toBeInTheDocument();
    expect(screen.getByText("Developing — real progress alongside real gaps.")).toBeInTheDocument();
  });
});
