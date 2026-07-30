import { act, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { axe } from "jest-axe";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisStatusPage } from "../src/pages/AnalysisStatusPage";
import * as api from "../src/services/api";
import { MockEventSource } from "./testUtils/mockEventSource";
import { makeAnalysis } from "./testUtils/analysisFixture";

function renderPage(startupId = "startup-1") {
  return render(
    <MemoryRouter initialEntries={[`/startups/${startupId}/status`]}>
      <Routes>
        <Route path="/startups/:startupId/status" element={<AnalysisStatusPage />} />
        <Route path="/analyses/:analysisId" element={<p>Reveal (stub)</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AnalysisStatusPage", () => {
  beforeEach(() => {
    MockEventSource.reset();
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("kicks off analysis immediately and shows the Forging sequence", async () => {
    vi.spyOn(api, "analyzeStartup").mockResolvedValue(makeAnalysis({ id: "a1", status: "RUNNING" }));
    renderPage();
    expect(await screen.findByText(/thinking through your venture/i)).toBeInTheDocument();
    expect(api.analyzeStartup).toHaveBeenCalledWith("startup-1");
  });

  it("navigates to the Reveal the moment the real analysis completes", async () => {
    vi.spyOn(api, "analyzeStartup").mockResolvedValue(makeAnalysis({ id: "a1", status: "RUNNING" }));
    renderPage();
    await screen.findByText(/thinking through your venture/i);

    const source = MockEventSource.instances[0];
    act(() => {
      source.emit(makeAnalysis({ id: "a1", status: "COMPLETED" }));
    });

    expect(await screen.findByText(/reveal \(stub\)/i)).toBeInTheDocument();
  });

  it("shows a retry control when the request itself fails", async () => {
    vi.spyOn(api, "analyzeStartup").mockRejectedValue(new Error("network down"));
    renderPage();
    expect(await screen.findByRole("button", { name: /retry analysis/i })).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    vi.spyOn(api, "analyzeStartup").mockResolvedValue(makeAnalysis({ id: "a1", status: "RUNNING" }));
    const { container } = renderPage();
    await screen.findByText(/thinking through your venture/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});
