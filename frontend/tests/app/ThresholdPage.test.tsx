import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { ThresholdPage } from "../../src/pages/ThresholdPage";

function renderThreshold() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<ThresholdPage />} />
        <Route path="/new/idea" element={<div>opening line screen</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ThresholdPage", () => {
  it("renders landing-background.jpg as the hero artwork, with only History/About/Get Started as real HTML", () => {
    // The artwork itself carries the wordmark/headline/tagline/feature blocks — this component
    // must never re-create any of that in HTML (see the module docstring), so the only asserted
    // content here is the three controls a static image can't provide.
    renderThreshold();
    const hero = screen.getByAltText("", { selector: "img" }) as HTMLImageElement;
    expect(hero.src).toContain("landing-background");
    expect(screen.getByRole("link", { name: /history/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /about/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /get started/i })).toBeInTheDocument();
  });

  it("never renders fabricated/unattributed testimonials", () => {
    // Ruthless-honesty pass: unattributed quotes with no name or company are fabricated social
    // proof on a product with no users yet — removed rather than reworded (see
    // ThresholdPage.tsx's module docstring). Guards against them silently reappearing.
    renderThreshold();
    expect(screen.queryByText(/found the pricing model/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/told me the truth about my market size/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/gave me a plan for the next 90 days/i)).not.toBeInTheDocument();
  });

  it("navigates to the Opening Line (Discovery) after Get Started is pressed", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    renderThreshold();
    fireEvent.click(screen.getByRole("button", { name: /get started/i }));
    await act(async () => {
      vi.advanceTimersByTime(300);
    });
    vi.useRealTimers();
    await waitFor(() => expect(screen.getByText("opening line screen")).toBeInTheDocument());
  });

  it("has no accessibility violations", async () => {
    const { container } = renderThreshold();
    expect(await axe(container)).toHaveNoViolations();
  });
});
