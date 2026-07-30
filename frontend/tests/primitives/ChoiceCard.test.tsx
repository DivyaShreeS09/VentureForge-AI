import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { ChoiceCard } from "../../src/primitives/ChoiceCard";

describe("ChoiceCard", () => {
  it("exposes radio semantics by default", () => {
    render(<ChoiceCard label="Restaurant owners" selected={false} onSelect={() => {}} />);
    expect(screen.getByRole("radio", { name: "Restaurant owners" })).toBeInTheDocument();
  });

  it("exposes checkbox semantics in multi mode", () => {
    render(<ChoiceCard label="Restaurant owners" selected={false} onSelect={() => {}} mode="multi" />);
    expect(screen.getByRole("checkbox", { name: "Restaurant owners" })).toBeInTheDocument();
  });

  it("calls onSelect when clicked", () => {
    const onSelect = vi.fn();
    render(<ChoiceCard label="Restaurant owners" selected={false} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("radio", { name: "Restaurant owners" }));
    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("reflects selected state via aria-checked", () => {
    render(<ChoiceCard label="Restaurant owners" selected onSelect={() => {}} />);
    expect(screen.getByRole("radio", { name: "Restaurant owners" })).toHaveAttribute("aria-checked", "true");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<ChoiceCard label="Restaurant owners" selected onSelect={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
