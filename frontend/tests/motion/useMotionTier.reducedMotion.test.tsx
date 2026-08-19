import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useMotionTier } from "../../src/motion/transitions";

// See useMotionTier.test.tsx's header comment: the reduced-motion mock must be primed
// before framer-motion's first render in *this* file, since its useReducedMotion()
// caches the media-query result in a module-level singleton on first read.
window.matchMedia = () => ({
  matches: true,
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

describe("useMotionTier — reduced motion", () => {
  afterEach(cleanup);

  it("collapses the scene tier to a 150ms linear fade", () => {
    render(<Probe tier="scene" />);
    const result = JSON.parse(screen.getByTestId("probe").textContent!);
    expect(result).toEqual({ duration: 0.15, ease: "linear" });
  });

  it("collapses the threshold tier to a 150ms linear fade", () => {
    render(<Probe tier="threshold" />);
    const result = JSON.parse(screen.getByTestId("probe").textContent!);
    expect(result).toEqual({ duration: 0.15, ease: "linear" });
  });

  it("leaves the micro tier untouched — it carries meaning, not spectacle", () => {
    render(<Probe tier="micro" />);
    const result = JSON.parse(screen.getByTestId("probe").textContent!);
    expect(result.duration).toBe(0.12);
  });
});
