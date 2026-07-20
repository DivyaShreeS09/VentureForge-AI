import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RoadmapSection } from "../../src/components/results/studio/RoadmapSection";
import { buildMentorInterpretation } from "../fixtures/analysisFixtures";

describe("RoadmapSection", () => {
  it("renders First Week, First Month, and Next 90 Days columns", () => {
    render(<RoadmapSection mentor={buildMentorInterpretation()} />);
    expect(screen.getByText("First Week")).toBeInTheDocument();
    expect(screen.getByText("First Month")).toBeInTheDocument();
    expect(screen.getByText("Next 90 Days")).toBeInTheDocument();
  });

  it("shows priority, estimated effort, expected outcome, and dependencies per task", () => {
    render(<RoadmapSection mentor={buildMentorInterpretation()} />);
    expect(screen.getAllByText("Priority 1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Estimated effort:/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Expected outcome:/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Dependencies:/).length).toBeGreaterThanOrEqual(1);
  });

  it("shows an empty-state note for an empty bucket", () => {
    const mentor = buildMentorInterpretation({ validation_plan: [], roadmap_30_60_90: [] });
    render(<RoadmapSection mentor={mentor} />);
    expect(screen.getAllByText("Nothing scheduled for this window yet.").length).toBe(3);
  });
});
