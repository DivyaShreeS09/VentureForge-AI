import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ValidationPlanSection } from "../../src/components/results/studio/ValidationPlanSection";
import { buildMentorInterpretation } from "../fixtures/analysisFixtures";

describe("ValidationPlanSection", () => {
  it("renders top assumptions with how-to-test, success metric, failure signal, time, and learning", () => {
    render(<ValidationPlanSection validationPlan={buildMentorInterpretation().validation_plan} />);
    expect(screen.getByText("Is 'Traction' actually true/sufficient?")).toBeInTheDocument();
    expect(screen.getByText("How to test")).toBeInTheDocument();
    expect(screen.getByText("Success metric")).toBeInTheDocument();
    expect(screen.getByText("Failure signal")).toBeInTheDocument();
    expect(screen.getByText("Estimated time")).toBeInTheDocument();
    expect(screen.getByText("Expected learning")).toBeInTheDocument();
  });

  it("shows a reassuring empty state when nothing is left to validate", () => {
    render(<ValidationPlanSection validationPlan={[]} />);
    expect(screen.getByText(/nothing left to validate right now/)).toBeInTheDocument();
  });
});
