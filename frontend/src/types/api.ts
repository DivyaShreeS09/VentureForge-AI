export interface FundingAnswers {
  problem_clarity?: number | null;
  customer_pain_evidence?: number | null;
  market_size_evidence?: number | null;
  product_maturity?: number | null;
  traction?: number | null;
  revenue_model_clarity?: number | null;
  team_completeness?: number | null;
  competitive_differentiation?: number | null;
}

export interface Startup {
  id: string;
  name: string;
  description: string;
  funding_answers: FundingAnswers;
  created_at: string;
  updated_at: string;
}

export interface IndustryAlternative {
  industry: string;
  confidence: number;
}

export interface ExplanationTerm {
  term: string;
  kind?: "word" | "char";
  contribution: number;
  direction: "supports" | "opposes";
}

export interface Explanation {
  method: string;
  available: boolean;
  terms: ExplanationTerm[];
  note?: string;
}

export interface IndustryPrediction {
  predicted_industry: string;
  confidence: number;
  alternatives: IndustryAlternative[];
  model_version: string;
  model_pipeline?: string;
  explanation: Explanation;
  is_uncertain?: boolean;
  uncertainty_reasons?: string[];
}

export interface FundingBreakdownItem {
  dimension: string;
  label: string;
  raw_score: number;
  max_score: number;
  weight: number;
  weighted_contribution: number;
  scale_description: string;
}

export interface FundingAssessment {
  rubric_version: string;
  overall_score: number;
  level: "ready" | "developing" | "early_stage";
  breakdown: FundingBreakdownItem[];
  missing_evidence: string[];
  disclaimer: string;
}

export interface LlmNarrative {
  executive_summary: string;
  strategic_observations: string[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
}

export interface JudgeSummary {
  overall_assessment: string;
  strengths: string[];
  weaknesses: string[];
  missing_evidence: string[];
  next_actions: string[];
  confidence_level: "low" | "medium" | "high";
  source_attribution: Record<string, string>;
  /** Optional supplementary narrative from Gemini — present only when GEMINI_API_KEY is
   * configured server-side and the call succeeded. Never affects industry/confidence/score. */
  llm_narrative?: LlmNarrative | null;
}

export interface WorkflowTraceStep {
  node: string;
  status: string;
  detail: string | null;
}

export interface Analysis {
  id: string;
  startup_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  industry_model_version: string | null;
  industry_prediction: IndustryPrediction | null;
  funding_rubric_version: string | null;
  funding_assessment: FundingAssessment | null;
  judge_summary: JudgeSummary | null;
  workflow_trace: WorkflowTraceStep[] | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ModelStatus {
  industry_classifier_loaded: boolean;
  industry_classifier_version: string | null;
  industry_classifier_trained_at: string | null;
  funding_rubric_version: string;
}

/** Development-only aggregate health check (backend/app/api/v1/system_status.py). Not available
 * in production (404) — the frontend must fall back to a plain connectivity error in that case. */
export interface SystemStatus {
  api: { ok: boolean };
  database: { ok: boolean; detail: string | null };
  migrations: { up_to_date: boolean | null; detail: string | null };
  industry_model: { ok: boolean; version: string | null; detail: string | null };
  llm: { configured: boolean; detail: string | null };
}
