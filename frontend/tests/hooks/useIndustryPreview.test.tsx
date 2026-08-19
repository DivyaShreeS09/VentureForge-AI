import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useIndustryPreview } from "../../src/hooks/useIndustryPreview";
import * as api from "../../src/services/api";
import type { IndustryPreview } from "../../src/types/api";

const SAMPLE: IndustryPreview = {
  available: true,
  predicted_industry: "b2b",
  confidence: 0.82,
  is_uncertain: false,
  uncertainty_reasons: [],
  secondary_industry: "consumer",
  secondary_confidence: 0.1,
  model_version: "v2",
  customer_hints: [{ sector: "Hotels", matched_text: ["hotel"] }],
  detected_keywords: ["hotel"],
};

describe("useIndustryPreview", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("does not call the backend before the description clears the minimum length", () => {
    const spy = vi.spyOn(api, "previewIndustry");
    renderHook(({ name, description }) => useIndustryPreview(name, description), {
      initialProps: { name: "X", description: "short" },
    });
    act(() => vi.advanceTimersByTime(5000));
    expect(spy).not.toHaveBeenCalled();
  });

  it("debounces 2 seconds after typing stops before calling the backend", async () => {
    const spy = vi.spyOn(api, "previewIndustry").mockResolvedValue(SAMPLE);
    renderHook(({ name, description }) => useIndustryPreview(name, description), {
      initialProps: { name: "WasteLess", description: "A tool that helps hotel kitchens reduce waste." },
    });

    act(() => vi.advanceTimersByTime(1000));
    expect(spy).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(1500);
    });
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("reports the real preview once the backend responds", async () => {
    vi.spyOn(api, "previewIndustry").mockResolvedValue(SAMPLE);
    const { result } = renderHook(({ name, description }) => useIndustryPreview(name, description), {
      initialProps: { name: "WasteLess", description: "A tool that helps hotel kitchens reduce waste." },
    });

    await act(async () => {
      vi.advanceTimersByTime(2000);
      // Flush the already-resolved mock promise's microtask queue under fake timers —
      // `waitFor`'s polling can't help here since it relies on real timers.
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.preview).toEqual(SAMPLE);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("reports a transport error honestly, without fabricating a preview", async () => {
    vi.spyOn(api, "previewIndustry").mockRejectedValue(new Error("network down"));
    const { result } = renderHook(({ name, description }) => useIndustryPreview(name, description), {
      initialProps: { name: "WasteLess", description: "A tool that helps hotel kitchens reduce waste." },
    });

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.preview).toBeNull();
  });

  it("ignores a stale in-flight response once the description changes again", async () => {
    let resolveFirst!: (v: IndustryPreview) => void;
    const spy = vi.spyOn(api, "previewIndustry").mockImplementation(
      () => new Promise((resolve) => { resolveFirst = resolve; }),
    );

    const { result, rerender } = renderHook(
      ({ name, description }) => useIndustryPreview(name, description),
      { initialProps: { name: "X", description: "A tool that helps hotel kitchens reduce waste." } },
    );
    await act(async () => vi.advanceTimersByTime(2000));
    expect(spy).toHaveBeenCalledTimes(1);

    rerender({ name: "X", description: "A completely different idea about clinics and hospitals." });
    spy.mockResolvedValue({ ...SAMPLE, predicted_industry: "healthcare" });
    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
      await Promise.resolve();
    });

    // The first (stale) call finally resolves — must not overwrite the second's result.
    await act(async () => {
      resolveFirst(SAMPLE);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(result.current.preview?.predicted_industry).toBe("healthcare");
  });
});
