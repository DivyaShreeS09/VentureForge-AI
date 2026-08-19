import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UnderstandingMeter } from "../../src/components/evidence/UnderstandingMeter";

describe("UnderstandingMeter", () => {
  it("renders nothing before any evidence has been gathered", () => {
    const { container } = render(<UnderstandingMeter answers={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the real, renormalized evidence strength once answers exist", () => {
    render(
      <UnderstandingMeter
        answers={{
          problem_clarity: { state: "confirmed_positive", severity: 2 },
          traction: { state: "not_applicable", severity: null },
        }}
      />,
    );
    expect(screen.getByText(/evidence strength so far: 100%/i)).toBeInTheDocument();
  });
});
