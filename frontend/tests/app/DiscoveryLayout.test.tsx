import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";
import { DiscoveryLayout } from "../../src/app/DiscoveryLayout";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path={path}
          element={
            <DiscoveryLayout>
              <div>page content</div>
            </DiscoveryLayout>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("DiscoveryLayout", () => {
  it("reflects real, coarse route-level progress — half at idea, full at evidence", () => {
    renderAt("/new/idea");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
  });

  it("shows full progress on the evidence route", () => {
    renderAt("/new/evidence");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });

  it("opens a confirm-before-exit dialog on Escape, never navigates immediately", () => {
    renderAt("/new/idea");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(screen.getByText(/Your answers are saved/)).toBeInTheDocument();
  });

  it("opens the same confirm dialog when the wordmark is clicked, not a direct navigation", () => {
    renderAt("/new/idea");
    fireEvent.click(screen.getByRole("link", { name: /venture\s*forge\s*ai/i }));
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = renderAt("/new/idea");
    expect(await axe(container)).toHaveNoViolations();
  });
});
