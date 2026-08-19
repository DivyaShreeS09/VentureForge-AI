import type { Analysis } from "../../src/types/api";

export function makeAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  return {
    id: "analysis-1",
    startup_id: "startup-1",
    status: "RUNNING",
    current_node: null,
    current_stage: null,
    industry_model_version: null,
    industry_prediction: null,
    funding_rubric_version: null,
    funding_assessment: null,
    success_model_version: null,
    success_prediction: null,
    revenue_engine_version: null,
    revenue_estimate: null,
    market_intelligence: null,
    competitor_analysis: null,
    customer_personas: null,
    business_model: null,
    judge_summary: null,
    workflow_trace: null,
    error_message: null,
    positioning_correction_history: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}
