import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";
import { Chip } from "../../src/primitives/Chip";

describe("Chip", () => {
  it.each([
    ["confirmed", "Confirmed"],
    ["notSureYet", "Not sure yet"],
    ["risk", "Needs attention"],
  ] as const)("renders the %s state with its word, never color alone", (state, label) => {
    render(<Chip state={state} label={label} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("marks its color dot as decorative (aria-hidden) so meaning lives in the text", () => {
    const { container } = render(<Chip state="confirmed" label="Confirmed" />);
    expect(container.querySelector("[aria-hidden='true']")).not.toBeNull();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<Chip state="risk" label="Needs attention" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
