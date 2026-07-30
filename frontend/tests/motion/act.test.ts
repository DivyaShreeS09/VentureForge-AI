import { describe, expect, it } from "vitest";
import { actOfPath, tierForTransition } from "../../src/motion/act";

describe("actOfPath", () => {
  it.each([
    ["/new/idea", "discovery"],
    ["/new/evidence", "discovery"],
    ["/analyses/abc-123", "reveal"],
    ["/", "threshold"],
    ["/startups/abc-123/status", "threshold"],
    ["/history", "threshold"],
  ] as const)("classifies %s as %s", (path, act) => {
    expect(actOfPath(path)).toBe(act);
  });
});

describe("tierForTransition", () => {
  it("uses threshold on first mount (no previous pathname)", () => {
    expect(tierForTransition(null, "/")).toBe("threshold");
  });

  it("uses scene when moving within the same Act", () => {
    expect(tierForTransition("/new/idea", "/new/evidence")).toBe("scene");
  });

  it("uses threshold when crossing Acts", () => {
    expect(tierForTransition("/", "/new/idea")).toBe("threshold");
    expect(tierForTransition("/new/evidence", "/startups/abc/status")).toBe("threshold");
    expect(tierForTransition("/startups/abc/status", "/analyses/xyz")).toBe("threshold");
  });
});
