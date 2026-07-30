import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { TextField } from "../../src/primitives/TextField";

describe("TextField", () => {
  it("renders a single-line input by default", () => {
    render(<TextField label="Idea name" placeholder="e.g. WasteLess Kitchen" />);
    expect(screen.getByPlaceholderText("e.g. WasteLess Kitchen").tagName).toBe("INPUT");
  });

  it("renders a textarea when multiline", () => {
    render(<TextField label="Pitch" multiline placeholder="A one-line summary" />);
    expect(screen.getByPlaceholderText("A one-line summary").tagName).toBe("TEXTAREA");
  });

  it("calls onChange with the raw string value, not the event", () => {
    const onChange = vi.fn();
    render(<TextField label="Idea name" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Idea name"), { target: { value: "WasteLess Kitchen" } });
    expect(onChange).toHaveBeenCalledWith("WasteLess Kitchen");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<TextField label="Idea name" placeholder="e.g. WasteLess Kitchen" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
