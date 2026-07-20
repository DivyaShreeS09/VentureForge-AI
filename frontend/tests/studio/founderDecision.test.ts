import { describe, expect, it } from "vitest";
import { buildRoadmapBuckets, buildValidationDisplay, deriveFounderDecision } from "../../src/utils/founderDecision";
import { buildMentorInterpretation } from "../fixtures/analysisFixtures";

describe("deriveFounderDecision", () => {
  it("returns 'High Risk' when any founder_guidance_item is a confirmed_risk", () => {
    const mentor = buildMentorInterpretation({
      founder_guidance_items: [
        {
          dimension: "customer_pain_evidence", category: "confirmed_risk", status: "Confirmed risk",
          title: "Customers rejected this.", observation: "o", why_it_matters: "Real evidence of rejection.",
          next_step: "n", example: "e", priority: 1, evidence_state: "confirmed_negative", source: "deterministic",
        },
      ],
    });
    expect(deriveFounderDecision(mentor).label).toBe("High Risk");
  });

  it("returns 'Should Build' when readiness_level is 'ready' and no confirmed risk exists", () => {
    const mentor = buildMentorInterpretation({
      founder_guidance_items: [],
      mentor_verdict: { readiness_level: "ready", concise_verdict: "Ready.", strongest_signal: "s", biggest_risk: "b", immediate_priority: "p" },
    });
    expect(deriveFounderDecision(mentor).label).toBe("Should Build");
  });

  it("returns 'Proceed Carefully' when readiness_level is 'developing'", () => {
    const mentor = buildMentorInterpretation({ founder_guidance_items: [] });
    expect(deriveFounderDecision(mentor).label).toBe("Proceed Carefully");
  });

  it("returns 'Needs Validation' when readiness_level is 'early_stage'", () => {
    const mentor = buildMentorInterpretation({
      founder_guidance_items: [],
      mentor_verdict: { readiness_level: "early_stage", concise_verdict: "Early.", strongest_signal: "s", biggest_risk: "b", immediate_priority: "p" },
    });
    expect(deriveFounderDecision(mentor).label).toBe("Needs Validation");
  });

  it("always pairs the label with a concrete reason, never a bare judgment", () => {
    const mentor = buildMentorInterpretation();
    const decision = deriveFounderDecision(mentor);
    expect(decision.reason.length).toBeGreaterThan(10);
    expect(decision.detail.length).toBeGreaterThan(0);
  });
});

describe("buildRoadmapBuckets", () => {
  it("puts the top validation actions in First Week", () => {
    const mentor = buildMentorInterpretation();
    const { firstWeek } = buildRoadmapBuckets(mentor);
    expect(firstWeek.length).toBeGreaterThan(0);
    expect(firstWeek[0].task).toBe("Secure a pilot commitment");
    expect(firstWeek[0].outcome).toBe("Clear evidence.");
    expect(firstWeek[0].dependencies).toBe("Must be resolved before scaling.");
  });

  it("places days_31_60/days_61_90 roadmap activities into Next 90 Days", () => {
    const mentor = buildMentorInterpretation();
    const { next90Days } = buildRoadmapBuckets(mentor);
    const tasks = next90Days.map((t) => t.task);
    expect(tasks).toContain("Build the minimum workflow.");
    expect(tasks).toContain("Run the pilot.");
  });

  it("never drops a task — every roadmap/validation item appears in exactly one bucket", () => {
    const mentor = buildMentorInterpretation();
    const { firstWeek, firstMonth, next90Days } = buildRoadmapBuckets(mentor);
    const allTasks = [...firstWeek, ...firstMonth, ...next90Days].map((t) => t.task);
    expect(allTasks).toContain("Secure a pilot commitment");
    expect(allTasks).toContain("Build the minimum workflow.");
    expect(allTasks).toContain("Run the pilot.");
    // No duplicate: "Secure a pilot commitment" is the validation_plan method, and also happens to
    // be the days_1_30 roadmap activity in the fixture — it must appear only once overall.
    expect(allTasks.filter((t) => t === "Secure a pilot commitment")).toHaveLength(1);
  });
});

describe("buildValidationDisplay", () => {
  it("adds failure_signal, estimated_time, and expected_learning to every validation action", () => {
    const mentor = buildMentorInterpretation();
    const [display] = buildValidationDisplay(mentor.validation_plan);
    expect(display.failure_signal).toContain("Clear evidence.");
    expect(display.estimated_time.length).toBeGreaterThan(0);
    expect(display.expected_learning).toContain("traction");
  });
});
