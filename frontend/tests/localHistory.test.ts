import { beforeEach, describe, expect, it } from "vitest";
import { clearHistory, deleteHistoryEntry, listHistory, recordAnalysis } from "../src/services/localHistory";
import type { Analysis } from "../src/types/api";

function makeAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  return {
    id: "analysis-1",
    startup_id: "startup-1",
    status: "COMPLETED",
    industry_model_version: "v2",
    industry_prediction: {
      predicted_industry: "HealthTech",
      confidence: 0.53,
      alternatives: [],
      model_version: "v2",
      explanation: { method: "linear", available: true, terms: [] },
    },
    funding_rubric_version: "v1",
    funding_assessment: {
      rubric_version: "v1",
      overall_score: 32,
      level: "early_stage",
      breakdown: [],
      missing_evidence: [],
      disclaimer: "",
    },
    judge_summary: {
      overall_assessment: "",
      strengths: [],
      weaknesses: [],
      missing_evidence: [],
      next_actions: [],
      confidence_level: "low",
      source_attribution: {},
    },
    workflow_trace: [],
    error_message: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("localHistory", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("records a completed analysis and lists it back out", () => {
    recordAnalysis("Nova", makeAnalysis());
    const entries = listHistory();

    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({
      analysisId: "analysis-1",
      name: "Nova",
      industry: "HealthTech",
      score: 32,
      level: "early_stage",
    });
  });

  it("replaces an existing entry for the same analysis id instead of duplicating it", () => {
    recordAnalysis("Nova", makeAnalysis());
    recordAnalysis("Nova", makeAnalysis({ funding_assessment: { ...makeAnalysis().funding_assessment!, overall_score: 70 } }));

    const entries = listHistory();
    expect(entries).toHaveLength(1);
    expect(entries[0].score).toBe(70);
  });

  it("deletes a single entry by analysis id", () => {
    recordAnalysis("Nova", makeAnalysis());
    recordAnalysis("Atlas", makeAnalysis({ id: "analysis-2", startup_id: "startup-2" }));

    deleteHistoryEntry("analysis-1");
    const entries = listHistory();

    expect(entries).toHaveLength(1);
    expect(entries[0].name).toBe("Atlas");
  });

  it("clears all history", () => {
    recordAnalysis("Nova", makeAnalysis());
    clearHistory();
    expect(listHistory()).toHaveLength(0);
  });
});
