import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { Button } from "../../src/primitives/Button";

describe("Button", () => {
  it("renders as a real button with a 44px minimum hit target", () => {
    render(<Button>Begin</Button>);
    const button = screen.getByRole("button", { name: "Begin" });
    expect(button.tagName).toBe("BUTTON");
    expect(button.className).toMatch(/min-h-\[44px\]/);
    expect(button.className).toMatch(/min-w-\[44px\]/);
  });

  it("fires onClick when pressed", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Begin</Button>);
    fireEvent.click(screen.getByRole("button", { name: "Begin" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not fire onClick when disabled", () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        Begin
      </Button>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Begin" }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("has no accessibility violations in any variant", async () => {
    const { container } = render(
      <>
        <Button variant="primary">Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
      </>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
