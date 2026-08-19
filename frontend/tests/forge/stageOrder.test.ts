import { describe, expect, it } from "vitest";
import { deriveStageStatuses, STAGE_ORDER } from "../../src/components/forge/stageOrder";

describe("deriveStageStatuses", () => {
  it("marks every stage upcoming before any real stage has been reported", () => {
    const statuses = deriveStageStatuses(null, false);
    expect(statuses.every((s) => s.state === "upcoming")).toBe(true);
  });

  it("marks stages before the current one done, the current one current, the rest upcoming", () => {
    const statuses = deriveStageStatuses("Scoring Your Readiness", false);
    const byLabel = Object.fromEntries(statuses.map((s) => [s.label, s.state]));
    expect(byLabel["Reading Your Idea"]).toBe("done");
    expect(byLabel["Understanding Your Industry"]).toBe("done");
    expect(byLabel["Scoring Your Readiness"]).toBe("current");
    expect(byLabel["Comparing Historical Patterns"]).toBe("upcoming");
  });

  it("marks every stage done once the run is terminal, even the last-reached one", () => {
    const statuses = deriveStageStatuses(STAGE_ORDER[STAGE_ORDER.length - 1], true);
    expect(statuses.every((s) => s.state === "done")).toBe(true);
  });

  it("never invents a stage name outside the real, fixed order", () => {
    const statuses = deriveStageStatuses("Some Unknown Stage", false);
    // An unrecognized stage (e.g. a future backend addition this file hasn't been updated for
    // yet) must never crash or fabricate a "current" stage — everything just stays upcoming.
    expect(statuses.every((s) => s.state === "upcoming")).toBe(true);
  });
});
