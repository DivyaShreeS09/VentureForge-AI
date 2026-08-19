import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WhereYouAreScene } from "../../src/components/discovery/WhereYouAreScene";

describe("WhereYouAreScene", () => {
  it("renders all five stages with equal visual weight (a radiogroup, one selected at most)", () => {
    render(<WhereYouAreScene stage="" onSelect={vi.fn()} />);
    const group = screen.getByRole("radiogroup", { name: /where are you right now/i });
    expect(group).toBeInTheDocument();
    for (const label of ["Just an idea", "Validating", "Building", "Early customers", "Growing"]) {
      expect(screen.getByRole("radio", { name: label })).toBeInTheDocument();
    }
  });

  it("marks only the selected stage as checked", () => {
    render(<WhereYouAreScene stage="Validating" onSelect={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "Validating" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: "Building" })).toHaveAttribute("aria-checked", "false");
  });

  it("calls onSelect with the tapped stage", () => {
    const onSelect = vi.fn();
    render(<WhereYouAreScene stage="" onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("radio", { name: "Building" }));
    expect(onSelect).toHaveBeenCalledWith("Building");
  });
});
