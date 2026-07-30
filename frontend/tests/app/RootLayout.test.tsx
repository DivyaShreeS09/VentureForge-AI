import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { RootLayout } from "../../src/app/RootLayout";

vi.mock("../../src/services/api", () => ({
  getSystemStatus: vi.fn().mockResolvedValue(null),
  getModelsStatus: vi.fn().mockResolvedValue({
    industry_classifier_loaded: true,
    industry_classifier_version: "v1",
    industry_classifier_trained_at: null,
    funding_rubric_version: "v1",
  }),
}));

// The floating Dock (and its "?" About affordance) is global except on the Threshold itself
// ("/"), which now renders its own top-right History/About/Get Started nav directly over
// `landing-background.jpg` instead — so these tests render at a non-Threshold path, matching
// every other real route in the app.
function renderRoot(path = "/history") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <RootLayout>
        <div>page content</div>
      </RootLayout>
    </MemoryRouter>,
  );
}

describe("RootLayout", () => {
  it("renders page content once the (mocked, unreachable) system-status check settles", async () => {
    renderRoot();
    await waitFor(() => expect(screen.getByText("page content")).toBeInTheDocument());
  });

  it("provides a skip-to-content link as the first focusable element", async () => {
    renderRoot();
    await waitFor(() => screen.getByText("page content"));
    expect(screen.getByRole("link", { name: /skip to content/i })).toBeInTheDocument();
  });

  it("replaces the old persistent sidebar's About Model / Documentation with one small affordance", async () => {
    renderRoot();
    await waitFor(() => screen.getByText("page content"));
    fireEvent.click(screen.getByRole("button", { name: /about the model/i }));
    expect(await screen.findByText(/model/i, { selector: "h2, h1, p" })).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = renderRoot();
    await waitFor(() => screen.getByText("page content"));
    expect(await axe(container)).toHaveNoViolations();
  });
});
