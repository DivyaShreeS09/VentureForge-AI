import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";
import { ProgressFilament } from "../../src/primitives/ProgressFilament";

describe("ProgressFilament", () => {
  it("exposes real progressbar semantics, never a percentage/step label", () => {
    render(<ProgressFilament progress={0.5} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "50");
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/step/i)).not.toBeInTheDocument();
  });

  it("clamps out-of-range progress", () => {
    render(<ProgressFilament progress={1.4} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<ProgressFilament progress={0.5} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
