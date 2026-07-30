import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";
import { ForgeCore } from "../../src/components/forge/ForgeCore";

describe("ForgeCore", () => {
  it("renders the purple ring while running", () => {
    const { container } = render(<ForgeCore state="running" progress={0.4} />);
    expect(container.querySelector(".stroke-forge-accent-2")).toBeInTheDocument();
  });

  it("switches to the confirmed color once done", () => {
    const { container } = render(<ForgeCore state="done" progress={1} />);
    expect(container.querySelector(".stroke-forge-confirmed")).toBeInTheDocument();
  });

  it("switches to the risk color on error", () => {
    const { container } = render(<ForgeCore state="error" progress={0.2} />);
    expect(container.querySelector(".stroke-forge-risk")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<ForgeCore state="running" progress={0.5} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
