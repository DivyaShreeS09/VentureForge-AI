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

  // `analyzeStartup` resolves on its own microtask; the heading renders before that resolves, so
  // a test that returns as soon as the heading appears can let that resolution (and the
  // `EventSource` construction it triggers via `useAnalysisProgress`) land after this test's own
  // `afterEach` has already run `vi.unstubAllGlobals()` — intermittently throwing "EventSource is
  // not defined" under load. Every test that expects the subscription to actually exist waits for
  // it explicitly first, so nothing outstanding leaks past the test boundary.
  async function waitForEventSourceConnected() {
    await vi.waitFor(() => expect(MockEventSource.instances.length).toBeGreaterThan(0));
  }

  it("kicks off analysis immediately and shows the Forging sequence", async () => {
    vi.spyOn(api, "analyzeStartup").mockResolvedValue(makeAnalysis({ id: "a1", status: "RUNNING" }));
    renderPage();
    expect(await screen.findByText(/thinking through your venture/i)).toBeInTheDocument();
    expect(api.analyzeStartup).toHaveBeenCalledWith("startup-1");
    await waitForEventSourceConnected();
  });

  it("navigates to the Reveal the moment the real analysis completes", async () => {
    vi.spyOn(api, "analyzeStartup").mockResolvedValue(makeAnalysis({ id: "a1", status: "RUNNING" }));
    renderPage();
    await screen.findByText(/thinking through your venture/i);
    await waitForEventSourceConnected();

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
    await waitForEventSourceConnected();
    expect(await axe(container)).toHaveNoViolations();
  });
});
