import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RootErrorBoundary } from "../../src/app/RootErrorBoundary";

function Bomb(): never {
  throw new Error("simulated render crash");
}

describe("RootErrorBoundary", () => {
  it("renders a recoverable message instead of unmounting silently when a child throws", () => {
    // React logs the error to the console by default even when caught here — expected noise,
    // not a real failure.
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <RootErrorBoundary>
        <Bomb />
      </RootErrorBoundary>,
    );
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reload/i })).toBeInTheDocument();
  });

  it("renders children normally when nothing throws", () => {
    render(
      <RootErrorBoundary>
        <p>real content</p>
      </RootErrorBoundary>,
    );
    expect(screen.getByText("real content")).toBeInTheDocument();
  });
});
