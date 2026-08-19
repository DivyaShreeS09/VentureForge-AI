import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useMotionTier } from "../../src/motion/transitions";

// framer-motion's useReducedMotion() reads `prefers-reduced-motion` into a
// module-level singleton on first use, in-process, and never re-reads it — see
// node_modules/framer-motion/dist/es/utils/reduced-motion/use-reduced-motion.mjs. That
// singleton must be primed *before* framer-motion's first render in this file, so the
// mock is installed at module scope (before any test/render), not inside an `it`. The
// reduced-motion counterpart lives in useMotionTier.reducedMotion.test.tsx, in its own
// file, so it gets its own fresh module registry and singleton (vitest resets the
// module graph per test file by default).
window.matchMedia = () => ({
  matches: false,
  media: "",
  addEventListener: () => {},
  removeEventListener: () => {},
  addListener: () => {},
  removeListener: () => {},
  dispatchEvent: () => false,
});

function Probe({ tier }: { tier: "micro" | "scene" | "threshold" }) {
  const transition = useMotionTier(tier);
  return <div data-testid="probe">{JSON.stringify(transition)}</div>;
}

describe("useMotionTier — motion not reduced", () => {
  afterEach(cleanup);

  it.each([
    ["micro", 0.12],
    ["scene", 0.28],
    ["threshold", 0.56],
  ] as const)("returns the full-duration %s preset unchanged", (tier, duration) => {
    render(<Probe tier={tier} />);
    const result = JSON.parse(screen.getByTestId("probe").textContent!);
    expect(result.duration).toBe(duration);
  });
});
