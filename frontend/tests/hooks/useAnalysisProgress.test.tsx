import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAnalysisProgress } from "../../src/hooks/useAnalysisProgress";
import { MockEventSource } from "../testUtils/mockEventSource";
import { makeAnalysis } from "../testUtils/analysisFixture";

describe("useAnalysisProgress", () => {
  beforeEach(() => {
    MockEventSource.reset();
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses real SSE messages into the analysis state", async () => {
    const { result } = renderHook(() => useAnalysisProgress("a1"));
    const source = MockEventSource.instances[0];

    act(() => {
      source.emit(makeAnalysis({ status: "RUNNING", current_stage: "Reading Your Idea" }));
    });

    await waitFor(() => expect(result.current.analysis?.current_stage).toBe("Reading Your Idea"));
    expect(result.current.connected).toBe(true);
  });

  it("reflects each new real event as it arrives, not just the first", async () => {
    const { result } = renderHook(() => useAnalysisProgress("a1"));
    const source = MockEventSource.instances[0];

    act(() => source.emit(makeAnalysis({ status: "RUNNING", current_stage: "Reading Your Idea" })));
    await waitFor(() => expect(result.current.analysis?.current_stage).toBe("Reading Your Idea"));

    act(() => source.emit(makeAnalysis({ status: "RUNNING", current_stage: "Scoring Your Readiness" })));
    await waitFor(() => expect(result.current.analysis?.current_stage).toBe("Scoring Your Readiness"));
  });

  it("closes the connection once a terminal status arrives", async () => {
    const { result } = renderHook(() => useAnalysisProgress("a1"));
    const source = MockEventSource.instances[0];

    act(() => source.emit(makeAnalysis({ status: "COMPLETED" })));

    await waitFor(() => expect(result.current.analysis?.status).toBe("COMPLETED"));
    expect(source.closed).toBe(true);
  });

  it("does nothing when there is no analysis id yet", () => {
    const { result } = renderHook(() => useAnalysisProgress(null));
    expect(result.current.analysis).toBeNull();
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("ignores a malformed event instead of crashing", async () => {
    const { result } = renderHook(() => useAnalysisProgress("a1"));
    const source = MockEventSource.instances[0];

    act(() => {
      source.onmessage?.({ data: "not json" });
    });
    act(() => source.emit(makeAnalysis({ status: "RUNNING", current_stage: "Reading Your Idea" })));

    await waitFor(() => expect(result.current.analysis?.current_stage).toBe("Reading Your Idea"));
  });
});
