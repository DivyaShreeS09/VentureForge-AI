import "@testing-library/jest-dom";
import { expect } from "vitest";
import { toHaveNoViolations } from "jest-axe";

// Build Contract §1.10 / §3 — every primitive's Definition of Done requires zero
// axe-core violations. Registered globally so no individual test file needs to repeat
// this wiring.
expect.extend(toHaveNoViolations);

// jsdom doesn't implement IntersectionObserver (used by CommandCapsule to track which
// Reveal section is currently in view) — this is a test-environment gap, not
// something real browsers lack, so it's stubbed globally rather than mocked per test.
if (typeof globalThis.IntersectionObserver === "undefined") {
  class IntersectionObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // @ts-expect-error -- minimal stub; real browsers provide the full interface.
  globalThis.IntersectionObserver = IntersectionObserverStub;
}

// jsdom doesn't implement ResizeObserver either — Recharts' `ResponsiveContainer`
// (used by the Reveal dashboard's radar/bar charts) requires it to measure its
// container, and its absence was silently hanging the whole test worker rather than
// throwing a clear error. Same rationale as the IntersectionObserver stub above.
if (typeof globalThis.ResizeObserver === "undefined") {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // @ts-expect-error -- minimal stub; real browsers provide the full interface.
  globalThis.ResizeObserver = ResizeObserverStub;
}
