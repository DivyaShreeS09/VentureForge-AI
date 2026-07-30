import { describe, expect, it } from "vitest";
import {
  acknowledgmentFor,
  computeEvidenceStrength,
  EVIDENCE_DIMENSIONS,
} from "../../src/components/evidence/evidenceDimensions";
import type { FundingAnswers } from "../../src/types/api";

describe("computeEvidenceStrength", () => {
  it("is 0 with no answers yet", () => {
    expect(computeEvidenceStrength({})).toBe(0);
  });

  it("excludes not_applicable dimensions from both numerator and denominator", () => {
    const answers: FundingAnswers = {
      problem_clarity: { state: "confirmed_positive", severity: 2 },
      traction: { state: "not_applicable", severity: null },
    };
    // Only problem_clarity counts: 2 / (1 * 2) = 100%, not diluted by the opted-out dimension.
    expect(computeEvidenceStrength(answers)).toBe(100);
  });

  it("never rewards a confirmed_negative or not_sure_yet answer", () => {
    const answers: FundingAnswers = {
      problem_clarity: { state: "confirmed_negative", severity: null },
      traction: { state: "not_sure_yet", severity: null },
    };
    expect(computeEvidenceStrength(answers)).toBe(0);
  });
});

describe("acknowledgmentFor", () => {
  it("never fabricates a positive spin on a confirmed_negative answer", () => {
    expect(acknowledgmentFor("confirmed_negative", null)).toMatch(/not a flaw/i);
  });

  it("treats not_sure_yet as an open question, not a weakness", () => {
    expect(acknowledgmentFor("not_sure_yet", null)).toMatch(/not a weakness/i);
  });
});

describe("EVIDENCE_DIMENSIONS stage notes", () => {
  it("only offers a stage note for early-stage founders on stage-sensitive dimensions", () => {
    const traction = EVIDENCE_DIMENSIONS.find((d) => d.key === "traction")!;
    expect(traction.stageNote?.("Just an idea")).toBeTruthy();
    expect(traction.stageNote?.("Growing")).toBeNull();
  });

  it("dimensions with no stage sensitivity never render a note", () => {
    const problemClarity = EVIDENCE_DIMENSIONS.find((d) => d.key === "problem_clarity")!;
    expect(problemClarity.stageNote).toBeUndefined();
  });
});
