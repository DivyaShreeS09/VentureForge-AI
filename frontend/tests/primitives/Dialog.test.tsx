import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { Dialog } from "../../src/primitives/Dialog";

describe("Dialog", () => {
  it("renders nothing when closed", () => {
    render(
      <Dialog
        open={false}
        message="Discard this draft?"
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("states exactly what will happen — never a generic 'Are you sure?'", () => {
    render(
      <Dialog
        open
        message="Discard this draft? Your answers so far will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.getByText("Discard this draft? Your answers so far will be lost.")).toBeInTheDocument();
    expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
  });

  it("calls onConfirm and onCancel from their respective buttons", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <Dialog
        open
        message="Discard this draft?"
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Discard" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("closes on Escape", () => {
    const onCancel = vi.fn();
    render(
      <Dialog
        open
        message="Discard this draft?"
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("has no accessibility violations while open", async () => {
    const { container } = render(
      <Dialog
        open
        message="Discard this draft?"
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
