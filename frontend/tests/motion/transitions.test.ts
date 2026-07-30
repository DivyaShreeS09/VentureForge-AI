import { describe, expect, it } from "vitest";
import { motionTiers } from "../../src/motion/transitions";

describe("motionTiers", () => {
  it("defines exactly the three Design System Bible §8 durations, in seconds", () => {
    expect(motionTiers.micro.duration).toBe(0.12);
    expect(motionTiers.scene.duration).toBe(0.28);
    expect(motionTiers.threshold.duration).toBe(0.56);
  });

  it("uses the specified easing curves — a shared decelerating settle for scene/threshold", () => {
    expect(motionTiers.micro.ease).toEqual([0.4, 0, 0.2, 1]);
    expect(motionTiers.scene.ease).toEqual([0.16, 1, 0.3, 1]);
    expect(motionTiers.threshold.ease).toEqual(motionTiers.scene.ease);
  });

  it("exposes exactly three tiers — no fourth duration exists", () => {
    expect(Object.keys(motionTiers)).toEqual(["micro", "scene", "threshold"]);
  });
});
